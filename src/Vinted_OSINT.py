"""
Copyright (C) 2024-2026  Johannes Habel

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import asyncio
import json
import argparse
import re
from pathlib import Path
from dataclasses import dataclass, field

from base_api import BaseCore
from base_api.modules.errors import AccessDeniedError
from colorama import Fore, init
from prettytable import PrettyTable
from rich.console import Console
from rich.table import Table as RichTable
from rich.panel import Panel
from rich import box
from rich.text import Text
from rich_argparse import RichHelpFormatter

console = Console()

init(autoreset=True)

@dataclass
class BatchResult:
    users: dict[str, dict] = field(default_factory=dict)
    failures: dict[str, str] = field(default_factory=dict)


async def run_main(argv=None):
    parser = argparse.ArgumentParser(
        prog="Vinted OSINT", description="Retrieve public Vinted user information",
        formatter_class=RichHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-u", "--user_id", help="User ID")
    group.add_argument("-ul", "--user_list", help="File containing one user ID per line")
    parser.add_argument("-e", "--extension", default=".com", help="Regional extension, e.g. .fr or .de")
    parser.add_argument("-c", "--license", action="store_true", help="Licensing and acknowledgements")
    parser.add_argument("-a", "--fetch_all", action="store_true", help="Include all API fields in the report")
    parser.add_argument("--no_export", action="store_true", help="Disable exports")
    parser.add_argument("-f", "--export_format", choices=["json", "csv", "html", "latex", "txt"])
    parser.add_argument("--output-dir", type=Path, default=Path('.'), help="Export directory")
    args = parser.parse_args(argv)
    if args.license:
        console.print("Vinted OSINT — GPL-3.0-or-later\nDeveloped by Johannes Habel / EchterAlsFake\n"
                      "Libraries: eaf_base_api, colorama, prettytable, rich, rich-argparse\n"
                      "Authentication inspiration: https://github.com/herissondev/vinted-api-wrapper")
        return 0
    if not (args.user_id or args.user_list):
        parser.error("provide --user_id or --user_list")
    try:
        client = OSINT(args.user_id, args.user_list, extension=args.extension,
                       export_format=None if args.no_export else args.export_format,
                       fetch_all=args.fetch_all, output_dir=args.output_dir)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    result = await client.start()
    return 1 if result.failures else 0


class OSINT:
    """Fetch users and coordinate independent reports; options are instance-local."""

    def __init__(self, username=None, username_list=None, *, extension=".com",
                 export_format=None, fetch_all=False, output_dir=Path('.'), core=None):
        if (username is None) == (username_list is None):
            raise ValueError("provide exactly one user ID or user-list file")
        if not re.fullmatch(r"\.[a-z]{2,}", extension):
            raise ValueError("extension must be a regional suffix such as .com or .fr")
        if export_format not in (None, "json", "csv", "html", "latex", "txt"):
            raise ValueError("unsupported export format")
        ids = [str(username)] if username is not None else Path(username_list).read_text(encoding="utf-8").splitlines()
        self.usernames = list(dict.fromkeys(uid.strip() for uid in ids if uid.strip()))
        if not self.usernames or any(not re.fullmatch(r"[0-9]+", uid) for uid in self.usernames):
            raise ValueError("user IDs must contain digits only; user lists must not be empty")
        self.extension = extension
        self.VINTED_AUTH_URL = f"https://www.vinted{extension}"
        self.export_format = export_format
        self.fetch_all = fetch_all
        self.output_dir = Path(output_dir)
        self.core = core if core is not None else BaseCore()
        self.core.default_headers.update({'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'en'})

    async def start(self):
        result = BatchResult()
        try:
            for user_id in self.usernames:
                try:
                    user = await self.get_information(user_id)
                    report = UserReport(user, fetch_all=self.fetch_all)
                    report.print_everything()
                    if self.export_format:
                        report.export(user_id, self.export_format, self.output_dir)
                    result.users[user_id] = user
                except Exception as error:
                    result.failures[user_id] = f"{type(error).__name__}: {error}"
                    console.print(f"Failed user {user_id}: {error}", style="red", markup=False)
        finally:
            await self.core.close()
        console.print(f"Completed: {len(result.users)} succeeded, {len(result.failures)} failed.")
        return result

    async def get_information(self, username):
        print(f"{Fore.LIGHTGREEN_EX}[+]{Fore.LIGHTCYAN_EX}Fetching information for: {username}")

        retries = 5
        for i in range(retries):
            print(f"{Fore.LIGHTGREEN_EX}[+]{Fore.LIGHTYELLOW_EX}Requesting: {self.VINTED_AUTH_URL}/api/v2/users/{username} [{i}/{retries}]")
            try:
                data = await self.core.request(url=f"{self.VINTED_AUTH_URL}/api/v2/users/{username}")
            except AccessDeniedError:
                if i == retries - 1:
                    raise
                await self.authentication_flow()
            else:
                payload = data.json()
                if not isinstance(payload, dict) or not isinstance(payload.get("user"), dict) or not payload["user"]:
                    raise ValueError("API response must contain a non-empty user object")
                user = payload["user"]
                if str(user.get("id")) != str(username):
                    raise ValueError("API response user ID does not match the requested ID")
                return user

    async def authentication_flow(self):
        self.core.initialize_session()
        self.core.session.cookies.clear()
        await self.core.request(method="POST", url=self.VINTED_AUTH_URL)
        print(f"{Fore.LIGHTGREEN_EX}[+]{Fore.LIGHTYELLOW_EX}Authentication Success!")


class UserReport:
    """Format and export a fetched user without changing the source data."""

    def __init__(self, user, *, fetch_all=False):
        self.dictionary = user
        self.fetch_all = fetch_all
        self.main_table = PrettyTable(["Category", "Variable", "Value"])
        self.photo_table = PrettyTable(["Category", "Variable", "Value"])
        self.discount_table = PrettyTable(["Category", "Variable", "Value"])
        self.payment_table = PrettyTable(["ID", "Code", "Requires Credit Card", "Event Tracking Code", "Icon",
                                          "Enabled", "Translated Name", "Note", "Method Change Possible"])
        self.create_tables()

    def create_tables(self):

        categories = {
            "User Info": [
                "id", "anon_id", "login", "real_name", "email", "birthday", "city", "city_id",
                "country_title", "country_title_local", "country_id", "country_code", "country_iso_code",
                "profile_url", "share_profile_url", "is_online", "last_loged_on", "last_loged_on_ts"
            ],
            "Account Status": [
                "account_status", "is_account_banned", "account_ban_date", "action_restriction", "moderator",
                "is_catalog_moderator", "is_catalog_role_marketing_photos", "is_hated", "hates_you",
                "can_view_profile", "is_favourite"
            ],
            "Preferences": [
                "is_publish_photos_agreed", "expose_location", "third_party_tracking",
                "allow_direct_messaging", "localization", "locale", "iso_locale_code", "hide_feedback"
            ],
            "Statistics": [
                "item_count", "given_item_count", "taken_item_count", "followers_count", "following_count",
                "following_brands_count", "positive_feedback_count", "neutral_feedback_count",
                "negative_feedback_count", "meeting_transaction_count", "feedback_reputation",
                "feedback_count", "total_items_count"
            ],
            "Other": [
                "path", "contacts_permission", "contacts", "photo", "bundle_discount", "can_bundle", "fundraiser",
                "business_account_id", "has_ship_fast_badge", "about", "avg_response_time",
                "carrier_ids", "carriers_without_custom_ids", "updated_on", "msg_template_count",
                "business_account", "business", "default_address", "code", "currency", "facebook_user_id",
                "is_bpf_price_prominence_applied"
            ]
        }

        for category, variables in categories.items():
            self.add_rows(self.main_table, category, variables, self.dictionary)


        if self.fetch_all:
            known = {name for names in categories.values() for name in names}
            self.add_rows(self.main_table, "Additional API Fields",
                          sorted(set(self.dictionary) - known), self.dictionary)

        photo_data = self.dictionary.get("photo", None)
        if not photo_data is None:
            self.photo_table = PrettyTable()
            self.photo_table.field_names = ["Category", "Variable", "Value"]
            self.photo_table.add_row(["Photo", "ID", photo_data.get("id", "N/A")])
            self.photo_table.add_row(["Photo", "Width", photo_data.get("width", "N/A")])
            self.photo_table.add_row(["Photo", "Height", photo_data.get("height", "N/A")])
            self.photo_table.add_row(["Photo", "URL", photo_data.get("url", "N/A")])
            self.photo_table.add_row(["Photo", "Dominant Color", photo_data.get("dominant_color", "N/A")])
            self.photo_table.add_row(["Photo", "Dominant Color Opaque", photo_data.get("dominant_color_opaque", "N/A")])
            self.photo_table.add_row(["Photo", "Is Suspicious", photo_data.get("is_suspicious", "N/A")])
            self.photo_table.add_row(["Photo", "Full Size URL", photo_data.get("full_size_url", "N/A")])
            self.photo_table.add_row(["Photo", "Is Hidden", photo_data.get("is_hidden", "N/A")])

            # Extract thumbnails data
            thumbnails = photo_data.get("thumbnails", [])
            for thumbnail in thumbnails:
                self.photo_table.add_row(
                    ["Thumbnails", f"Type ({thumbnail.get('type', 'N/A')})", thumbnail.get("url", "N/A")])
                self.photo_table.add_row(
                    ["Thumbnails", f"Width ({thumbnail.get('type', 'N/A')})", thumbnail.get("width", "N/A")])
                self.photo_table.add_row(
                    ["Thumbnails", f"Height ({thumbnail.get('type', 'N/A')})", thumbnail.get("height", "N/A")])

        bundle_discount = self.dictionary.get("bundle_discount", None)
        if not bundle_discount is None:
            self.discount_table.add_row(["Bundle Discount", "ID", bundle_discount.get("id", "N/A")])
            self.discount_table.add_row(["Bundle Discount", "User ID", bundle_discount.get("user_id", "N/A")])
            self.discount_table.add_row(["Bundle Discount", "Enabled", bundle_discount.get("enabled", "N/A")])
            self.discount_table.add_row(
                ["Bundle Discount", "Minimal Item Count", bundle_discount.get("minimal_item_count", "N/A")])

            # Extract discounts data
            discounts = bundle_discount.get("discounts", [])
            for discount in discounts:
                self.discount_table.add_row(["Discounts", f"Minimal Item Count ({discount.get('minimal_item_count', 'N/A')})",
                               discount.get("fraction", "N/A")])

        # Extract verification data safely
        verification_data = self.dictionary.get("verification", {})
        if verification_data:
            for method, details in verification_data.items():
                if isinstance(details, dict):
                    is_valid = details.get("valid", "N/A")
                    verified_at = details.get("verified_at", "N/A")
                    self.main_table.add_row(["Verification", f"{method.capitalize()} Valid", str(is_valid)])
                    if verified_at and verified_at != "N/A":
                        self.main_table.add_row(
                            ["Verification", f"{method.capitalize()} Verified At", str(verified_at)])


        payment_methods = self.dictionary.get("accepted_pay_in_methods", None)
        if payment_methods is not None:
            self.create_payment_table(payment_methods)

    @staticmethod
    def evaluate_seller_risk(data):
        """Return reported observations and missing evidence, without a safety score."""
        observations, missing = [], []
        for key, label in (("is_account_banned", "Account ban reported"),
                           ("action_restriction", "Account restriction reported")):
            if key not in data or data[key] is None:
                missing.append(key)
            elif data[key]:
                observations.append(label)
        for key in ("feedback_count", "negative_feedback_count", "feedback_reputation"):
            value = data.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                observations.append(f"{key.replace('_', ' ').capitalize()}: {value}")
            else:
                missing.append(key)
        photo = data.get("photo")
        if isinstance(photo, dict) and isinstance(photo.get("is_suspicious"), bool):
            if photo["is_suspicious"]:
                observations.append("API marks the profile photo as suspicious")
        else:
            missing.append("photo.is_suspicious")
        verification = data.get("verification")
        if isinstance(verification, dict) and verification:
            for name, details in verification.items():
                if isinstance(details, dict) and isinstance(details.get("valid"), bool):
                    observations.append(f"{name} verification: {'reported valid' if details['valid'] else 'reported invalid'}")
                else:
                    missing.append(f"verification.{name}")
        else:
            missing.append("verification")
        return observations, missing

    def add_rows(self, table, category, variables, dictionary):
        for var in variables:
            value = dictionary.get(var)
            formatted_value = self.format_value(var, value)
            table.add_row([category, var, formatted_value])


    def create_payment_table(self, payment_methods):
        self.payment_table.field_names = ["ID", "Code", "Requires Credit Card", "Event Tracking Code", "Icon",
                                     "Enabled", "Translated Name", "Note", "Method Change Possible"]

        # Add rows to the payment table based on the payment methods
        for payment in payment_methods:
            self.payment_table.add_row([payment.get('id'), payment.get('code'), payment.get('requires_credit_card'),
                                   payment.get('event_tracking_code'), payment.get('icon'), payment.get('enabled'),
                                   payment.get('translated_name'), payment.get('note'),
                                   payment.get('method_change_possible')])

    def format_value(self, variable, value):
        """Format the value to handle None and nested data."""
        if value is None:
            return "N/A"
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    def _print_rich_table(self, pt, title):
        if not pt.rows:
            return False
        rich_table = RichTable(title=title, box=box.ROUNDED, header_style="bold magenta", border_style="cyan", title_style="bold yellow")
        for field in pt.field_names:
            rich_table.add_column(field, style="bright_white")
        for row in pt.rows:
            rich_table.add_row(*[str(item) for item in row])
        console.print(rich_table)
        console.print()
        return True

    # Main method to print everything
    def print_everything(self):
        self.main_table.sortby = "Category"
        self.discount_table.sortby = "Category"
        self.photo_table.sortby = "Category"

        self._print_rich_table(self.main_table, "Main Information")
        if not self._print_rich_table(self.photo_table, "Photo Information"):
            print(f"{Fore.LIGHTRED_EX}[!]{Fore.LIGHTWHITE_EX}No photo data has been found.")
        if not self._print_rich_table(self.discount_table, "Discount Information"):
            print(f"{Fore.LIGHTRED_EX}[!]{Fore.LIGHTWHITE_EX}No discount data has been found.")
        if not self._print_rich_table(self.payment_table, "Payment Information"):
            print(f"{Fore.LIGHTRED_EX}[!]{Fore.LIGHTWHITE_EX}No payment data has been found.")


        observations, missing = self.evaluate_seller_risk(self.dictionary)
        text = Text("Public profile observations do not establish seller reliability or fraud.\n\n")
        for observation in observations:
            text.append(f"• {observation}\n")
        if missing:
            text.append("\nUnavailable or unrecognized data: " + ", ".join(missing))
        console.print(Panel(text, title="Seller profile observations", border_style="cyan"))

    def export(self, user_id, export_format, output_dir=Path('.')):
        if not re.fullmatch(r"[0-9]+", str(user_id)):
            raise ValueError("user IDs must contain digits only")
        serializers = {"json": "get_json_string", "csv": "get_csv_string", "html": "get_html_string",
                       "latex": "get_latex_string", "txt": "get_string"}
        if export_format not in serializers:
            raise ValueError("unsupported export format")
        directory = Path(output_dir) / str(user_id)
        directory.mkdir(parents=True, exist_ok=True)
        paths = []
        for name in ("main", "photo", "discount", "payment"):
            table = getattr(self, f"{name}_table")
            path = directory / f"data_{name}_{user_id}.{export_format}"
            path.write_text(getattr(table, serializers[export_format])(), encoding="utf-8")
            paths.append(path)
        console.print(f"Exported {len(paths)} files to {directory}", markup=False)
        return paths


def main():
    raise SystemExit(asyncio.run(run_main()))

if __name__ == "__main__":
    raise SystemExit(asyncio.run(run_main()))
