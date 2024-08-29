<h1 align="center">Vinted Osint</h1>
<h5 align="center">an OSINT tool for Vinted.com</h5>


# Features:
- Fetching User information
- Fetching multiple users
- No Login required
- Pretty formatting
- Export data in multiple formats

# Installation
- Pypi: `pip install Vinted_OSINT`
- Git: `pip install git+https://github.com/EchterAlsFake/Vinted_OSINT`
- From source: `git clone https://github.com/EchterAlsFake/Vinted_OSINT && cd Vinted_OSINT && pip install -r requirements.txt`

# Usage

> [!IMPORTANT]
> You need to give a User ID, not a name!
> The User ID is inside the URL for example: `vinted.com/member/146483126-bonnjeff1`
> <br>
> The User ID is: `146483126`

Fetch a single user: `$ vinted -u <user id> `
Fetch multiple users: `$ vinted --user_list <user_file>`

> [!NOTE]
> The user IDs in the file should be separated with new lines.

`-u` and `--user_list` can't be used together (obviously)
### Other arguments

- `--extension` -> Specify a custom extension, e.g, `.fr` or `.de`
- `--license` -> Displays license information
- `--fetch_all` -> Fetches also the payment information
- `--no_export` -> Data won't be exported
- `--export_format` -> Specify export format [json,csv,html,latex,txt]

# Credits / Acknowledgements

- Big thanks to: [Vinted-API-Wrapper](https://github.com/herissondev/vinted-api-wrapper), it gave me the idea, how to do 
  the authentication flow.
- Thanks to: [keskivonfer](https://github.com/megadose/keskivonfer) for the inspiration

Libraries used:

- [requests](https://github.com/psf/requests)
- [colorama](https://github.com/tartley/colorama)
- [fake_useragent](https://github.com/fake-useragent/fake-useragent)
- [prettytable](https://github.com/jazzband/prettytable)


# Contributions
Any contribution is appreciated. If you have feedback, issues or want to help,
don't hesitate to do so.

# License
Vinted Osint is licensed under [GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html)
<br>Copyright 2024 Johannes Habel


