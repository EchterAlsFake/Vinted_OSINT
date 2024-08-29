"""
Copyright (C) 2024  Johannes Habel

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

import json
import argparse
import os.path
import requests

from fake_useragent import UserAgent
from colorama import Fore, init
from prettytable import PrettyTable

init(autoreset=True)

parser = argparse.ArgumentParser(
    prog="Vinted OSINT",
    description="An Open-Source intelligent Tool to get information about User/s on Vinted"
)

# Mutually exclusive group for username or user list
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("-u", "--username", help="Username")
group.add_argument("-ul", "--user_list", help="List of user names, separated by new line")

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
username = args.username
username_list = args.user_list
fetch_all = args.fetch_all

# Determine export format and handle warnings if necessary
export_format = args.export_format if args.export_format else "json"

if export and not args.export_format:
    export = False  # Disable export if no format is provided
    print(f"{Fore.LIGHTRED_EX}[!]{Fore.LIGHTYELLOW_EX}Warning: {Fore.LIGHTWHITE_EX}You did not set an export format, "
          f"no data will be saved to a file.")


class OSINT:
    def __init__(self, username, username_list):
        self.session = requests.Session()
        self.VINTED_AUTH_URL = f"https://www.vinted{extension}/auth/token_refresh"
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

        ua = UserAgent()
        HEADERS = {
            'User-Agent': ua.firefox,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en',
            'DNT': '1',
            'Connection': 'keep-alive',
            'TE': 'Trailers'
        }

        self.session.headers.update(HEADERS)
        self.dictionary = None
        self.start()

    def start(self):
        for username_ in self.usernames:
            self.setup_tables()
            self.dictionary = self.get_information(username_)
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


    def get_information(self, username):
        print(f"{Fore.LIGHTGREEN_EX}[+]{Fore.LIGHTCYAN_EX}Fetching information for: {username}")

        retries = 5
        for i in range(retries):
            data = self.session.get(url=f"https://www.vinted{extension}/api/v2/users/{username}")
            if data.status_code == 401:
                self.authentication_flow()

            else:
                return json.loads(data.content.decode("utf-8"))["user"]

    def create_tables(self):

        categories = {
            "User Info": [
                "id", "anon_id", "login", "real_name", "email", "birthday", "city", "country_title",
                "country_title_local", "profile_url", "share_profile_url", "is_online", "last_loged_on"
            ],
            "Account Status": [
                "account_status", "is_account_ban_permanent", "account_ban_date", "moderator",
                "is_catalog_moderator", "is_catalog_role_marketing_photos", "is_hated", "hates_you",
                "can_view_profile", "is_favourite"
            ],
            "Preferences": [
                "is_publish_photos_agreed", "expose_location", "third_party_tracking",
                "allow_direct_messaging", "localization", "locale"
            ],
            "Statistics": [
                "item_count", "given_item_count", "taken_item_count", "followers_count", "following_count",
                "following_brands_count", "positive_feedback_count", "neutral_feedback_count",
                "negative_feedback_count", "meeting_transaction_count", "feedback_reputation",
                "feedback_count", "total_items_count"
            ],
            "Verification": [
                "email_verification", "facebook_verification", "google_verification"
            ],
            "Other": [
                "path", "contacts_permission", "contacts", "photo", "bundle_discount", "fundraiser",
                "business_account_id", "has_ship_fast_badge", "about", "avg_response_time",
                "carrier_ids", "carriers_without_custom_ids", "updated_on", "msg_template_count",
                "business_account", "business", "default_address", "code"
            ]
        }  # Categories for the main table

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

        payment_methods = self.dictionary.get("accepted_pay_in_methods", None)
        if payment_methods is not None:
            self.create_payment_table(payment_methods)



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

    # Main method to print everything
    def print_everything(self):
        self.main_table.sortby = "Category"
        self.discount_table.sortby = "Category"
        self.photo_table.sortby = "Category"

        print(self.main_table) if not len(self.main_table.rows) < 2 else None
        print(self.photo_table) if not len(self.photo_table.rows) < 2 else print(f"{Fore.LIGHTRED_EX}[!]{Fore.LIGHTWHITE_EX}No photo data has been found.")
        print(self.discount_table) if not len(self.discount_table.rows) < 2 else print(f"{Fore.LIGHTRED_EX}[!]{Fore.LIGHTWHITE_EX}No discount data has been found.")
        print(self.payment_table) if not len(self.payment_table.rows) < 2 else print(f"{Fore.LIGHTRED_EX}[!]{Fore.LIGHTWHITE_EX}No payment data has been found.")

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


    def authentication_flow(self):
        self.session.cookies.clear_session_cookies()

        try:
            self.session.post(self.VINTED_AUTH_URL)
            print(f"{Fore.LIGHTGREEN_EX}[+]{Fore.LIGHTYELLOW_EX}Authentication Success!")

        except Exception as e:
            print(e)

OSINT(username=username, username_list=username_list)
