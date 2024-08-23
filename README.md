<h1 align="center">Vinted Osint</h1>
<h5 align="center">an OSINT tool for Vinted.com</h5>


# Features:
- Fetching User information
- Fetching multiple users
- No Login required
- Export data in json and csv format

# Installation
- Pypi: `pip install Vinted_OSINT`
- Git: `pip install git+https://github.com/EchterAlsFake/Vinted_OSINT`
- From source: `git clone https://github.com/EchterAlsFake/Vinted_OSINT && cd Vinted_OSINT && pip install -r requirements.txt`

# Usage
Fetch a single user: `$ vinted -u <username> `
Fetch multiple users: `$ vinted --user-list <user_file>`

> [!NOTE]
> The usernames in the file should be separated with new lines.

### Other arguments

- `--extension` -> Specify a custom extension, e.g, `.fr` or `.de`
- `--license` -> Displays license information
- `--fetch_all` -> Fetches also the payment information
- `--no-export` -> Data won't be exported
- `--export_format` -> Specify export format [json, csv]

# Credits / Acknowledgements

- Big thanks to: [Vinted-API-Wrapper](https://github.com/herissondev/vinted-api-wrapper), it gave me the idea, how to do 
  the authentication flow.
- Thanks to: [keskivonfer](https://github.com/megadose/keskivonfer) for the inspiration

Libraries used:

- [requests](https://github.com/psf/requests)
- [colorama](https://github.com/tartley/colorama)
- [fake_useragent](https://github.com/fake-useragent/fake-useragent)
- [prettytable](https://github.com/jazzband/prettytable)


# License
Vinted Osint is licensed under [GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html)
<br>Copyright 2024 Johannes Habel


