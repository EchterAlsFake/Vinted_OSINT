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
import os.path

from base_api import BaseCore
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

async def run_main():
    global export, extension, username, username_list, fetch_all, export_format

    parser = argparse.ArgumentParser(
        prog="Vinted OSINT",
        description="An Open-Source intelligent Tool to get information about User/s on Vinted",
        formatter_class=RichHelpFormatter
    )

    # Mutually exclusive group for username or user list
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-u", "--user_id", help="User ID")
    group.add_argument("-ul", "--user_list", help="List of user IDs, separated by new line")

    # Additional arguments
    parser.add_argument("-e", "--extension", help="The website extension e.g. .fr .com .de", default=".com")
    parser.add_argument("-c", "--license", help="Licensing and copyright information", action="store_true")
    parser.add_argument("-a", "--fetch_all", help="Fetches literally ALL information", action="store_true")
    parser.add_argument("--no_export", help="If enabled, won't export any data", action="store_true")
    parser.add_argument("-f", "--export_format", help="Defines the export format [json, csv, html, latex, txt]",
                        choices=["json", "csv", "html", "latex", "txt"])

    # Parse arguments
    args = parser.parse_args()

    # Display license information
    if args.license:
        print("""
    Vinted Osint - 2024
    Developed by Johannes Habel | EchterAlsFake
    Licensed under GPLv3

    Used projects:
    - requests
    - colorama
    - prettytable
    - fake_useragent 

    Thanks to: https://github.com/herissondev/vinted-api-wrapper for the idea how to do the authentication stuff
        """)
        exit(0)

    # Set default values based on arguments
    export = not args.no_export  # Export is enabled unless --no_export is set
    extension = args.extension
    username = args.user_id
    username_list = args.user_list
    fetch_all = args.fetch_all

    # Determine export format and handle warnings if necessary
    export_format = args.export_format if args.export_format else "json"

    if export and not args.export_format:
        export = False  # Disable export if no format is provided
        print(
            f"{Fore.LIGHTRED_EX}[!]{Fore.LIGHTYELLOW_EX}Warning: {Fore.LIGHTWHITE_EX}You did not set an export format, "
            f"no data will be saved to a file.")

    await OSINT(username=username, username_list=username_list).start()


class OSINT:
    def __init__(self, username, username_list):
        self.core = BaseCore()
        self.VINTED_AUTH_URL = f"https://www.vinted{extension}"
        self.dicts = None
        self.payment_table = None
        self.main_table = None
        self.discount_table = None
        self.photo_table = None

        if not username is None:
            self.usernames = [username]

        elif not username_list is None:
            with open(username_list, "r") as users:
                self.usernames = users.read().splitlines()

        HEADERS = {
            'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36" ,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en',
            'DNT': '1',
            'Connection': 'keep-alive',
            'TE': 'Trailers'
        }

        self.core.initialize_session()
        self.core.session.headers.update(HEADERS)
        self.dictionary = None

    async def start(self):
        for username_ in self.usernames:
            self.setup_tables()
            self.dictionary = await self.get_information(username_)
            self.create_tables()
            self.print_everything()
            self.clear_tables()


    def clear_tables(self):
        self.photo_table.clear()
        self.main_table.clear()
        self.discount_table.clear()
        self.payment_table.clear()
        self.dictionary.clear()
        self.dicts.clear()


    def setup_tables(self):
        self.dicts = {}

        self.payment_table = PrettyTable()

        self.main_table = PrettyTable()
        self.main_table.field_names = ["Category", "Variable", "Value"]

        self.photo_table = PrettyTable()
        self.photo_table.field_names = ["Category", "Variable", "Value"]

        self.discount_table = PrettyTable()
        self.discount_table.field_names = ["Category", "Variable", "Value"]


    async def get_information(self, username):
        print(f"{Fore.LIGHTGREEN_EX}[+]{Fore.LIGHTCYAN_EX}Fetching information for: {username}")

        retries = 5
        for i in range(retries):
            print(f"{Fore.LIGHTGREEN_EX}[+]{Fore.LIGHTYELLOW_EX}Requesting: https://www.vinted{extension}/api/v2/users/{username} [{i}/{retries}]")
            data = await self.core.fetch(url=f"https://www.vinted{extension}/api/v2/users/{username}", get_response=True)

            if data.status_code == 401:
                await self.authentication_flow()

            else:
                return json.loads(data.content.decode("utf-8"))["user"]

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

    def evaluate_seller_risk(self, data):
        if not data:
            return "Unknown", 0

        score = 100
        flags = []
        # 1. Critical Hard Checks
        if data.get("is_account_banned") or data.get("action_restriction"):
            return "SCAMMER / BANNED", 0

        if data.get("photo"):
            if data.get("photo", {}).get("is_suspicious"):
                score -= 40
                flags.append("Suspicious profile photo flag")

        # 2. Feedback Analysis
        feedback_count = data.get("feedback_count", 0)
        reputation = data.get("feedback_reputation", 0.0)
        negatives = data.get("negative_feedback_count", 0)

        if feedback_count == 0:
            score -= 25
            flags.append("Zero feedback history")
        elif reputation < 0.90:
            score -= 20
            flags.append(f"Low reputation rating ({reputation * 100}%)")
        if negatives > 3:
            score -= 15
            flags.append(f"Multiple negative feedbacks ({negatives})")

        # 3. Verification Check
        verifications = data.get("verification", {})
        verified_methods = sum(
            1 for method in verifications.values() if isinstance(method, dict) and method.get("valid")
        )
        if verified_methods < 2:
            score -= 15
            flags.append("Weak account verification (less than 2 methods)")

        # 4. Activity Check
        if data.get("given_item_count", 0) == 0 and data.get("item_count", 0) > 10:
            score -= 10
            flags.append("High item listing volume but 0 successful sales")

        # Determine Tier
        if score >= 80:
            status = "Good Seller (Safe)"
        elif score >= 50:
            status = "Caution (Potential Risk)"
        else:
            status = "High Risk / Likely Scammer"

        return status, max(0, score), flags

    def add_rows(self, table, category, variables, dictionary):
        for var in variables:
            value = dictionary.get(var)
            formatted_value = self.format_value(var, value)
            table.add_row([category, var, formatted_value])


    # Function to create and display the payment table if fetch_all is True
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
        if isinstance(value, dict):
            self.dicts.update({variable: value})

        else:
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


        status, score, flags = self.evaluate_seller_risk(data=self.dictionary)
        risk_color = "red" if score < 50 else "yellow" if score < 80 else "green"

        risk_text = Text()
        risk_text.append("Based on the Provided API data a risk of the seller has been calculated.\nThis is only an estimate and does not guarantee or prove anything.\n\n", style="bold")
        risk_text.append(f"Risk Score: {score} - {status}\n", style=f"bold {risk_color}")
        if flags:
            risk_text.append("\nFlags:\n", style="bold red")
            for flag in flags:
                risk_text.append(f" - {flag}\n", style="yellow")

        console.print(Panel(risk_text, title="Seller Risk Evaluation", border_style="cyan"))


        mapping_main = {
            "json": self.main_table.get_json_string(),
            "html": self.main_table.get_html_string(),
            "csv": self.main_table.get_csv_string(),
            "latex": self.main_table.get_latex_string(),
            "txt": self.main_table.get_string()
        }

        mapping_photo = {
            "json": self.photo_table.get_json_string(),
            "html": self.photo_table.get_html_string(),
            "csv": self.photo_table.get_csv_string(),
            "latex": self.photo_table.get_latex_string(),
            "txt": self.photo_table.get_string()
        }

        mapping_discount = {
            "json": self.discount_table.get_json_string(),
            "csv": self.discount_table.get_csv_string(),
            "latex": self.discount_table.get_latex_string(),
            "txt": self.discount_table.get_string(),
            "html": self.discount_table.get_html_string()
        }

        mapping_payment = {
            "json": self.payment_table.get_json_string(),
            "csv": self.payment_table.get_csv_string(),
            "latex": self.payment_table.get_latex_string(),
            "txt": self.payment_table.get_string(),
            "html": self.payment_table.get_html_string()
        }


        if export:
            data = [
                mapping_main.get(export_format),
                mapping_photo.get(export_format),
                mapping_discount.get(export_format),
                mapping_payment.get(export_format),
            ]

            for idx, data_ in enumerate(data):
                if idx == 0:
                    filename = f"data_main_{username}.{export_format}"

                elif idx == 1:
                    filename = f"data_photo_{username}.{export_format}"

                elif idx == 2:
                    filename = f"data_discount_{username}.{export_format}"

                elif idx == 3:
                    filename = f"data_payment_{username}.{export_format}"

            print(f"{Fore.LIGHTMAGENTA_EX}Data was exported in: .{export_format}")

            if not os.path.exists(username):
                os.mkdir(username)

            with open(f"{username}{os.sep}{filename}", "w") as file:
                file.write(str(data))


    async def authentication_flow(self):
        self.core.session.cookies.clear()

        try:
            await self.core.fetch(method="POST", url=self.VINTED_AUTH_URL)
            print(f"{Fore.LIGHTGREEN_EX}[+]{Fore.LIGHTYELLOW_EX}Authentication Success!")

        except Exception as e:
            print(e)


def main():
    asyncio.run(run_main())

if __name__ == "__main__":
    asyncio.run(run_main())
