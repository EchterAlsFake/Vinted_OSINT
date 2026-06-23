<h1 align="center">Vinted OSINT</h1>
<h5 align="center">An OSINT tool for Vinted.com</h5>

# Features
- **Seller risk evaluation**: Calculates a risk score and lists potential red flags to identify scammers.
- **Fetching User information**: Retrieve details such as account status, preference settings, statistics, user information, verification methods, bundle discounts, and payment methods.
- **Fetching multiple users**: Batch process multiple user IDs from a file.
- **No Login required**: Extracts public information without needing a Vinted account.
- **Pretty formatting**: Uses `rich` and `prettytable` for colorful and highly readable terminal output, including colorized argument parsing help.
- **Export data in multiple formats**: Save retrieved data locally in JSON, CSV, HTML, LaTeX, or TXT formats.

# Installation

- **PyPI**: `pip install Vinted_OSINT`
- **Git**: `pip install git+https://github.com/EchterAlsFake/Vinted_OSINT.git`
- **From Source**: 
  ```bash
  git clone https://github.com/EchterAlsFake/Vinted_OSINT
  cd Vinted_OSINT
  pip install .
  ```
  *(Note: The project uses `pyproject.toml` for modern dependency management. You can also use `uv` for faster installation.)*

# Usage

> [!IMPORTANT]
> You need to provide a **User ID**, not a username!
> The User ID is the number inside the user's profile URL. For example, in `vinted.com/member/146483126-bonnjeff1`
> <br>
> The User ID is: `146483126`

Fetch a single user:
```bash
Vinted_OSINT -u <user_id>
```

Fetch multiple users:
```bash
Vinted_OSINT --user_list <user_file>
```

> [!NOTE]
> The user IDs in the `<user_file>` should be separated by newlines.

`-u` and `--user_list` are mutually exclusive and cannot be used together.

### Other arguments

You can view the full colorful help menu by running `Vinted_OSINT -h`.

- `-e`, `--extension` -> Specify a custom regional Vinted extension (default is `.com`), e.g., `.fr` or `.de`
- `-c`, `--license` -> Displays license and acknowledgements
- `-a`, `--fetch_all` -> Fetches literally ALL information available
- `--no_export` -> If enabled, data won't be exported locally
- `-f`, `--export_format` -> Specify the export format (choices: `json`, `csv`, `html`, `latex`, `txt`. Default is `json`)

# Credits / Acknowledgements

- Big thanks to: [Vinted-API-Wrapper](https://github.com/herissondev/vinted-api-wrapper), which gave the idea on how to handle the authentication flow.
- Thanks to: [keskivonfer](https://github.com/megadose/keskivonfer) for the inspiration.

### Libraries used:
- [eaf_base_api](https://github.com/echteralsfake/eaf_base_api)
- [colorama](https://github.com/tartley/colorama)
- [prettytable](https://github.com/jazzband/prettytable)
- [rich](https://github.com/Textualize/rich)
- [rich-argparse](https://github.com/Textualize/rich-argparse)

# Contributions
Any contribution is appreciated. If you have feedback, issues, or want to help out, don't hesitate to open an issue or pull request!

# License
Vinted OSINT is licensed under the [GPLv3 License](https://www.gnu.org/licenses/gpl-3.0.en.html).
<br>Copyright 2024-2026 Johannes Habel
