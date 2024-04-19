import requests
from bs4 import BeautifulSoup
import csv
import os
from dotenv import load_dotenv

load_dotenv()

od_blacklist = ["22PP", "KK", "5PPPKKK", "6PPPKKK", "4PPPKKK"]
custom_normal_aliases = {
    "5LP": ["jab", "stand jab", "standing jab"],
    "2LP": ["crouch jab", "crouching jab"],
    "5MP": ["strong", "stand strong", "standing strong"],
    "2MP": ["crouch strong", "crouching strong"],
    "5HP": ["fierce", "stand fierce", "standing fierce"],
    "2HP": ["crouch fierce", "crouching fierce"],
    "5LK": ["short", "stand short", "standing short"],
    "2LK": ["crouch short", "crouching short"],
    "5MK": ["forward", "stand forward", "standing forward"],
    "2MK": ["crouch forward", "crouching forward"],
    "5HK": ["roundhouse", "stand roundhouse", "standing roundhouse"],
    "2HK": ["crouch roundhouse", "crouching roundhouse", "sweep"],
    "LPLK": ["throw"],
    "4LPLK": ["back throw"],
    "HPHK": ["DI"],
}
custom_special_aliases = {
    "deejay": {
        "Air Slasher": ["boom", "fireball", "air slash", "slash"],
        "Jackknife Maximum": ["DP"],
        "Roll Through Feint": ["feint"],
        "Quick Rolling Sobat": ["sobat"],
        "Double Rolling Sobat": ["sobat"],
        "Jus Cool": ["sway"],
        "Funky Slicer": ["sway low"],
        "Waning Moon": ["sway overhead"],
        "Juggling Dash": ["run"],
    },
    "juri": {
        "Fuhajin": ["fuha"],
        "Tensenrin": ["DP"],
        "Shiku-sen": ["dive kick"],
    },
}


def extract_data(character_name, html, column_names):
    soup = BeautifulSoup(html, "html.parser")

    # Find all movedata-flex-framedata divs
    movedata_list = soup.find_all("div", {"class": "movedata-flex-framedata"})

    scraped_data = []
    duplicate_keys = []
    for movedata in movedata_list:
        name_items = [
            div.text.strip()
            for div in movedata.find_all(
                "div", {"class": "movedata-flex-framedata-name-item"}
            )
        ]
        input = name_items[0]
        move_name = name_items[1]

        # Check for duplicates
        is_duplicate = False
        for row in scraped_data:
            if row["input"] == input and row["move_name"] == move_name:
                duplicate_keys.append({"input": input, "move_name": move_name})
                is_duplicate = True
                break
        if is_duplicate:
            continue

        table_rows = movedata.find("table").find_all("tr")[1:]  # Skip header row

        columns = {}

        for row in table_rows:
            cells = row.find_all("td")

            headers = [
                th.text.strip() for th in row.find_previous_sibling().find_all("th")
            ]

            for i, cell in enumerate(cells):
                header = headers[i]
                if header in column_names:
                    formatted_header = header.lower().replace(" ", "_")
                    columns[formatted_header] = cell.text.strip()

        is_special = False
        section = movedata.find_parent("section", {"class", "section-collapsible"})
        if section:
            section_heading = section.previous_sibling
            if container_has_text(section_heading, "Special Moves"):
                is_special = True

        aliases = generate_aliases(
            character_name, movedata, input, move_name, is_special
        )

        scraped_data.append(
            {"input": input, "move_name": move_name, "aliases": aliases, **columns}
        )

    return scraped_data, duplicate_keys


def generate_aliases(character_name, movedata, input, move_name, is_special):
    aliases = []

    # Tag supers with aliases
    main_container = movedata.find_parent("div", {"class": "movedata-container"})
    if container_has_text(main_container, "Level 1"):
        aliases.extend(["level 1", "level 1 super"])
    if container_has_text(main_container, "Level 2"):
        # Custom rule for Dee-Jay rythym
        if "~" not in input:
            aliases.extend(["level 2", "level 2 super"])
    if container_has_text(main_container, "Level 3"):
        if container_has_text(movedata, "(CA)"):
            aliases.extend(["CA", "critical art"])
        else:
            aliases.extend(["level 3", "level 3 super"])

    # Add custom aliases
    if character_name in custom_special_aliases:
        if move_name in custom_special_aliases[character_name]:
            aliases.extend(custom_special_aliases[character_name][move_name])

    if is_special:
        # Tag OD inputs with aliases
        if "KK" in input or "PP" in input:
            if input not in od_blacklist:
                aliases.extend(generate_prefixed_aliases("OD", move_name, aliases))
        # Tag Light/Medium/Heavy versions
        else:
            if "LP" in input or "LK" in input:
                aliases.extend(generate_prefixed_aliases("light", move_name, aliases))
            if "MP" in input or "MK" in input:
                aliases.extend(generate_prefixed_aliases("medium", move_name, aliases))
            if "HP" in input or "HK" in input:
                aliases.extend(generate_prefixed_aliases("heavy", move_name, aliases))
    else:
        if input in custom_normal_aliases:
            aliases.extend(custom_normal_aliases[input])

    return aliases


def container_has_text(container, text):
    return container.find(lambda tag: text in tag.text)


def generate_prefixed_aliases(prefix, move_name, aliases):
    prefixed_aliases = [prefix + " " + move_name]
    for alias in aliases:
        prefixed_aliases.append(prefix + " " + alias)
    return prefixed_aliases


def convert_to_csv(data, filename):
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = data[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in data:
            writer.writerow(row)


def login():
    login_url = os.environ["REST_API_LOGIN_URL"]
    credentials = {
        "username": os.environ["REST_API_USERNAME"],
        "password": os.environ["REST_API_PASSWORD"],
    }

    login_response = requests.post(login_url, json=credentials)

    if login_response.status_code != 200:
        print("Failed to retrieve access token.")
        exit(1)

    access_token = login_response.json()["accessToken"]
    return access_token


access_token = login()

pages = {
    "aki": "https://wiki.supercombo.gg/w/Street_Fighter_6/A.K.I.",
    "blanka": "https://wiki.supercombo.gg/w/Street_Fighter_6/Blanka",
    "cammy": "https://wiki.supercombo.gg/w/Street_Fighter_6/Cammy",
    "chunli": "https://wiki.supercombo.gg/w/Street_Fighter_6/Chun-Li",
    "deejay": "https://wiki.supercombo.gg/w/Street_Fighter_6/Dee_Jay",
    "dhalsim": "https://wiki.supercombo.gg/w/Street_Fighter_6/Dhalsim",
    "ed": "https://wiki.supercombo.gg/w/Street_Fighter_6/Ed",
    "honda": "https://wiki.supercombo.gg/w/Street_Fighter_6/E.Honda",
    "guile": "https://wiki.supercombo.gg/w/Street_Fighter_6/Guile",
    "jamie": "https://wiki.supercombo.gg/w/Street_Fighter_6/Jamie",
    "jp": "https://wiki.supercombo.gg/w/Street_Fighter_6/JP",
    "juri": "https://wiki.supercombo.gg/w/Street_Fighter_6/Juri",
    "ken": "https://wiki.supercombo.gg/w/Street_Fighter_6/Ken",
    "kimberly": "https://wiki.supercombo.gg/w/Street_Fighter_6/Kimberly",
    "lily": "https://wiki.supercombo.gg/w/Street_Fighter_6/Lily",
    "luke": "https://wiki.supercombo.gg/w/Street_Fighter_6/Luke",
    "manon": "https://wiki.supercombo.gg/w/Street_Fighter_6/Manon",
    "marisa": "https://wiki.supercombo.gg/w/Street_Fighter_6/Marisa",
    "rashid": "https://wiki.supercombo.gg/w/Street_Fighter_6/Rashid",
    "ryu": "https://wiki.supercombo.gg/w/Street_Fighter_6/Ryu",
    "zangief": "https://wiki.supercombo.gg/w/Street_Fighter_6/Zangief",
}
for name, URL in pages.items():
    response = requests.get(URL)
    scraped_data, duplicate_keys = extract_data(
        name,
        response.content,
        [
            "Startup",
            "Active",
            "Recovery",
            "Cancel",
            "Damage",
            "Guard",
            "On Hit",
            "On Block",
        ],
    )
    convert_to_csv(scraped_data, f"supercombo/{name}.csv")
    if len(duplicate_keys) > 0:
        convert_to_csv(duplicate_keys, f"supercombo/{name}_duplicates.csv")

    # PUT request to add scraped data to server database
    protected_url = f"{os.environ['REST_API_PROTECTED_URL']}/{name}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    response = requests.put(
        protected_url, json={"moves": scraped_data}, headers=headers
    )

    if response.status_code == 200:
        print(f"{name} PUT request successful")
    else:
        print(f"{name} PUT request failed: Status {response.status_code}")
