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

parser = argparse.ArgumentParser(prog="Vinted OSINT", description="An Open-Source intelligent Tool to get information"
                                                                  "about User/s on Vinted")
parser.add_argument("-u" , "--username", help="Username", required=False)
parser.add_argument("-ul", "--user_list", help="List of user names, separated by new line", required=False)
parser.add_argument("-e", "--extension", help="The website extension e,g .fr .com .de", required=False)
parser.add_argument("-c", "--license", help="Licensing and copyright information", required=False,
                    action="store_true")
parser.add_argument("-a", "--fetch_all", help="Fetches literally ALL information", required=False)
parser.add_argument("--no_export", help="If enabled, won't export any data", required=False,
                    action="store_true")
parser.add_argument("-f", "--export_format", help="Defines the export format [json,csv]", required=False)


args = parser.parse_args()

if args.license:
    print(f"""
Vinted Osint - 2024
Developed by Johannes Habel | EchterAlsFake
Licensed under GPLv3

Used projects:
- requests
- colorama
- prettytable

Thanks to: https://github.com/herissondev/vinted-api-wrapper for the idea how to do the authentication stuff
""")

if args.no_export:
    export = False

else:
    export = True

if args.extension:
    extension = args.extension

else:
    extension = ".com"

username = None
username_list = None

if args.username:
    username = args.username

elif args.user_list:
    username_list = args.user_list
if args.export_format is True:
    export_format = "json"

else:
    export_format = args.export_format

if args.fetch_all:
    fetch_all = True

else:
    fetch_all = False

if args.export_format is None:
    export = False
    print(f"{Fore.LIGHTRED_EX}[!]{Fore.LIGHTYELLOW_EX}Warning: {Fore.LIGHTWHITE_EX}You did not set an export format, no"
          f"data will be saved to a file.")


class OSINT:
    def __init__(self, username, username_list):
        self.session = requests.Session()
        self.VINTED_AUTH_URL = f"https://www.vinted{extension}/auth/token_refresh"

        if not username is None:
            _ = []
            _.append(username)
            self.usernames = _  # I know this is weird

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
            self.dictionary = self.get_information(username_)
            print(self.dictionary)
            self.print_everything()


    def get_information(self, username):
        print(f"{Fore.LIGHTGREEN_EX}[+]{Fore.LIGHTCYAN_EX}Fetching information for: {username}")

        retries = 5
        for i in range(retries):
            data = self.session.get(url=f"https://www.vinted{extension}/api/v2/users/{username}")
            if data.status_code == 401:
                self.authentication_flow()

            else:
                return json.loads(data.content.decode("utf-8"))["user"]

    from prettytable import PrettyTable

    # Function to add rows to the general table based on categories and variables
    def add_rows(self, table, category, variables, dictionary):
        for var in variables:
            value = dictionary.get(var)
            formatted_value = self.format_value(value)
            table.add_row([category, var, formatted_value])


    # Function to create and display the payment table if fetch_all is True
    def create_payment_table(self, payment_methods):
        payment_table = PrettyTable()
        payment_table.field_names = ["ID", "Code", "Requires Credit Card", "Event Tracking Code", "Icon",
                                     "Enabled", "Translated Name", "Note", "Method Change Possible"]

        # Add rows to the payment table based on the payment methods
        for payment in payment_methods:
            payment_table.add_row([payment.get('id'), payment.get('code'), payment.get('requires_credit_card'),
                                   payment.get('event_tracking_code'), payment.get('icon'), payment.get('enabled'),
                                   payment.get('translated_name'), payment.get('note'),
                                   payment.get('method_change_possible')])
        return payment_table

    def format_value(self, value):
        """Format the value to handle None and nested data."""
        if value is None:
            return "N/A"
        if isinstance(value, dict):
            return "; ".join(f"{k}: {v}" for k, v in value.items())
        return str(value)

    # Main method to print everything
    def print_everything(self):
        table = PrettyTable()
        table.field_names = ["Category", "Variable", "Value"]

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
        }

        # Add rows to the general table based on the categories
        for category, variables in categories.items():
            self.add_rows(table, category, variables, self.dictionary)

        # Sort the general table by Category and Variable
        table.sortby = "Category"
        print(table)

        # Process and display the payment table if fetch_all is True
        if fetch_all:
            payment_methods = self.dictionary.get("accepted_pay_in_methods", [])
            payment_table = self.create_payment_table(payment_methods)
            print(payment_table)

        if export:
            # Determine the export format and process accordingly
            if export_format == "json":
                data_base = table.get_json_string()
                data_payment = payment_table.get_json_string() if fetch_all else None

            elif export_format == "csv":
                data_base = table.get_csv_string()
                data_payment = payment_table.get_csv_string() if fetch_all else None

            else:
                data_base = None
                data_payment = None

            if not os.path.exists(username):
                os.mkdir(username)

            with open(f"{username}{os.sep}data.{export_format}", "w") as file:
                file.write(str(data_base))

            if fetch_all:
                with open(f"{username}{os.sep}data_payment.{export_format}", "w") as file_2:
                    file_2.write(str(data_payment))


    def authentication_flow(self):
        self.session.cookies.clear_session_cookies()

        try:
            self.session.post(self.VINTED_AUTH_URL)
            print(f"{Fore.LIGHTGREEN_EX}[+]{Fore.LIGHTYELLOW_EX}Authentication Success!")

        except Exception as e:
            print(e)

OSINT(username=username, username_list=username_list)













