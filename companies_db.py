"""
Curated database of top tech companies, startups, quant/trading firms
organized by location. Used when no input Excel is provided.
"""

# ── Location aliases ──────────────────────────────────────────────────────────
LOCATION_ALIASES: dict[str, list[str]] = {
    "san francisco": ["san francisco", "sf", "bay area", "silicon valley"],
    "new york":      ["new york", "nyc", "ny", "new york city"],
    "seattle":       ["seattle", "bellevue", "redmond"],
    "austin":        ["austin", "tx"],
    "boston":        ["boston", "cambridge", "ma"],
    "los angeles":   ["los angeles", "la", "santa monica", "culver city"],
    "chicago":       ["chicago", "il"],
    "london":        ["london", "uk"],
    "bangalore":     ["bangalore", "bengaluru", "india"],
    "remote":        ["remote", "anywhere", "worldwide"],
    "singapore":     ["singapore"],
    "toronto":       ["toronto", "canada"],
    "berlin":        ["berlin", "germany"],
}

# ── Company database ──────────────────────────────────────────────────────────
# Each entry: (name, domain, [locations], category)
# category: "big_tech" | "startup" | "quant" | "trading" | "fintech"
COMPANIES_DB: list[tuple[str, str, list[str], str]] = [

    # ── Big Tech ──────────────────────────────────────────────────────────────
    ("Google",        "google.com",        ["san francisco", "new york", "seattle", "austin", "los angeles", "chicago", "london", "bangalore", "singapore", "toronto", "remote"], "big_tech"),
    ("Meta",          "meta.com",          ["san francisco", "new york", "seattle", "austin", "los angeles", "london", "singapore", "remote"], "big_tech"),
    ("Apple",         "apple.com",         ["san francisco", "new york", "seattle", "austin", "london", "singapore", "remote"], "big_tech"),
    ("Microsoft",     "microsoft.com",     ["seattle", "san francisco", "new york", "austin", "london", "bangalore", "singapore", "toronto", "remote"], "big_tech"),
    ("Amazon",        "amazon.com",        ["seattle", "san francisco", "new york", "austin", "london", "bangalore", "singapore", "toronto", "remote"], "big_tech"),
    ("Netflix",       "netflix.com",       ["san francisco", "los angeles", "new york", "remote"], "big_tech"),
    ("Salesforce",    "salesforce.com",    ["san francisco", "new york", "seattle", "chicago", "london", "bangalore", "singapore", "toronto", "remote"], "big_tech"),
    ("Adobe",         "adobe.com",         ["san francisco", "seattle", "new york", "austin", "london", "bangalore", "remote"], "big_tech"),
    ("Oracle",        "oracle.com",        ["san francisco", "austin", "new york", "seattle", "london", "bangalore", "remote"], "big_tech"),
    ("IBM",           "ibm.com",           ["new york", "san francisco", "seattle", "austin", "chicago", "london", "bangalore", "remote"], "big_tech"),
    ("Intel",         "intel.com",         ["san francisco", "seattle", "austin", "london", "remote"], "big_tech"),
    ("Nvidia",        "nvidia.com",        ["san francisco", "seattle", "austin", "london", "remote"], "big_tech"),
    ("Qualcomm",      "qualcomm.com",      ["san francisco", "seattle", "austin", "london", "bangalore", "remote"], "big_tech"),
    ("Cisco",         "cisco.com",         ["san francisco", "seattle", "new york", "austin", "london", "bangalore", "singapore", "remote"], "big_tech"),
    ("VMware",        "vmware.com",        ["san francisco", "seattle", "austin", "london", "bangalore", "remote"], "big_tech"),
    ("SAP",           "sap.com",           ["san francisco", "new york", "chicago", "london", "berlin", "bangalore", "singapore", "remote"], "big_tech"),
    ("Workday",       "workday.com",       ["san francisco", "new york", "seattle", "london", "remote"], "big_tech"),
    ("ServiceNow",    "servicenow.com",    ["san francisco", "new york", "london", "remote"], "big_tech"),
    ("Snowflake",     "snowflake.com",     ["san francisco", "seattle", "new york", "remote"], "big_tech"),
    ("Databricks",    "databricks.com",    ["san francisco", "new york", "seattle", "remote"], "big_tech"),
    ("Palantir",      "palantir.com",      ["new york", "san francisco", "seattle", "london", "remote"], "big_tech"),
    ("Uber",          "uber.com",          ["san francisco", "new york", "seattle", "amsterdam", "bangalore", "remote"], "big_tech"),
    ("Lyft",          "lyft.com",          ["san francisco", "new york", "seattle", "remote"], "big_tech"),
    ("Airbnb",        "airbnb.com",        ["san francisco", "new york", "seattle", "london", "remote"], "big_tech"),
    ("Twitter",       "x.com",            ["san francisco", "new york", "seattle", "london", "remote"], "big_tech"),
    ("LinkedIn",      "linkedin.com",      ["san francisco", "new york", "chicago", "london", "bangalore", "remote"], "big_tech"),
    ("Spotify",       "spotify.com",       ["new york", "boston", "london", "remote"], "big_tech"),
    ("Slack",         "slack.com",         ["san francisco", "new york", "london", "remote"], "big_tech"),
    ("Zoom",          "zoom.us",           ["san francisco", "new york", "remote"], "big_tech"),
    ("Dropbox",       "dropbox.com",       ["san francisco", "new york", "remote"], "big_tech"),
    ("Box",           "box.com",           ["san francisco", "new york", "london", "remote"], "big_tech"),
    ("Atlassian",     "atlassian.com",     ["san francisco", "new york", "seattle", "austin", "london", "singapore", "remote"], "big_tech"),
    ("HubSpot",       "hubspot.com",       ["boston", "new york", "chicago", "london", "remote"], "big_tech"),
    ("Zendesk",       "zendesk.com",       ["san francisco", "new york", "london", "remote"], "big_tech"),
    ("Twilio",        "twilio.com",        ["san francisco", "new york", "remote"], "big_tech"),
    ("Okta",          "okta.com",          ["san francisco", "new york", "london", "remote"], "big_tech"),
    ("Cloudflare",    "cloudflare.com",    ["san francisco", "new york", "london", "remote"], "big_tech"),
    ("Datadog",       "datadog.com",       ["new york", "san francisco", "london", "remote"], "big_tech"),
    ("MongoDB",       "mongodb.com",       ["new york", "san francisco", "london", "remote"], "big_tech"),
    ("HashiCorp",     "hashicorp.com",     ["san francisco", "new york", "remote"], "big_tech"),
    ("Splunk",        "splunk.com",        ["san francisco", "new york", "london", "remote"], "big_tech"),
    ("Pagerduty",     "pagerduty.com",     ["san francisco", "new york", "remote"], "big_tech"),
    ("New Relic",     "newrelic.com",      ["san francisco", "new york", "remote"], "big_tech"),
    ("Elastic",       "elastic.co",        ["san francisco", "new york", "london", "remote"], "big_tech"),
    ("Confluent",     "confluent.io",      ["san francisco", "new york", "remote"], "big_tech"),
    ("Databricks",    "databricks.com",    ["san francisco", "new york", "remote"], "big_tech"),

    # ── High-growth Startups ──────────────────────────────────────────────────
    ("Stripe",        "stripe.com",        ["san francisco", "new york", "seattle", "london", "dublin", "remote"], "startup"),
    ("Figma",         "figma.com",         ["san francisco", "new york", "london", "remote"], "startup"),
    ("Discord",       "discord.com",       ["san francisco", "new york", "remote"], "startup"),
    ("Notion",        "notion.so",         ["san francisco", "new york", "remote"], "startup"),
    ("Airtable",      "airtable.com",      ["san francisco", "new york", "remote"], "startup"),
    ("Canva",         "canva.com",         ["san francisco", "new york", "london", "singapore", "remote"], "startup"),
    ("Ramp",          "ramp.com",          ["new york", "san francisco", "remote"], "startup"),
    ("Brex",          "brex.com",          ["san francisco", "new york", "remote"], "startup"),
    ("Plaid",         "plaid.com",         ["san francisco", "new york", "remote"], "startup"),
    ("Robinhood",     "robinhood.com",     ["san francisco", "new york", "remote"], "startup"),
    ("Coinbase",      "coinbase.com",      ["san francisco", "new york", "remote"], "startup"),
    ("OpenAI",        "openai.com",        ["san francisco", "remote"], "startup"),
    ("Anthropic",     "anthropic.com",     ["san francisco", "remote"], "startup"),
    ("Scale AI",      "scale.com",         ["san francisco", "new york", "remote"], "startup"),
    ("Cohere",        "cohere.com",        ["san francisco", "toronto", "london", "remote"], "startup"),
    ("Hugging Face",  "huggingface.co",    ["new york", "san francisco", "london", "remote"], "startup"),
    ("Stability AI",  "stability.ai",      ["san francisco", "london", "remote"], "startup"),
    ("Mistral AI",    "mistral.ai",        ["san francisco", "london", "remote"], "startup"),
    ("Anyscale",      "anyscale.com",      ["san francisco", "remote"], "startup"),
    ("Together AI",   "together.ai",       ["san francisco", "remote"], "startup"),
    ("Runway",        "runwayml.com",      ["new york", "san francisco", "remote"], "startup"),
    ("Midjourney",    "midjourney.com",    ["san francisco", "remote"], "startup"),
    ("Perplexity",    "perplexity.ai",     ["san francisco", "remote"], "startup"),
    ("Cursor",        "cursor.sh",         ["san francisco", "remote"], "startup"),
    ("Linear",        "linear.app",        ["san francisco", "new york", "remote"], "startup"),
    ("Vercel",        "vercel.com",        ["san francisco", "new york", "remote"], "startup"),
    ("Railway",       "railway.app",       ["san francisco", "remote"], "startup"),
    ("PlanetScale",   "planetscale.com",   ["san francisco", "remote"], "startup"),
    ("Supabase",      "supabase.com",      ["san francisco", "remote"], "startup"),
    ("Retool",        "retool.com",        ["san francisco", "remote"], "startup"),
    ("Rippling",      "rippling.com",      ["san francisco", "new york", "remote"], "startup"),
    ("Lattice",       "lattice.com",       ["san francisco", "remote"], "startup"),
    ("Gusto",         "gusto.com",         ["san francisco", "new york", "denver", "remote"], "startup"),
    ("Deel",          "deel.com",          ["san francisco", "new york", "remote"], "startup"),
    ("Remote",        "remote.com",        ["remote"], "startup"),
    ("Loom",          "loom.com",          ["san francisco", "remote"], "startup"),
    ("Grammarly",     "grammarly.com",     ["san francisco", "new york", "remote"], "startup"),
    ("Duolingo",      "duolingo.com",      ["pittsburgh", "new york", "remote"], "startup"),
    ("Coursera",      "coursera.org",      ["san francisco", "new york", "remote"], "startup"),
    ("Instacart",     "instacart.com",     ["san francisco", "toronto", "remote"], "startup"),
    ("DoorDash",      "doordash.com",      ["san francisco", "new york", "remote"], "startup"),
    ("Chime",         "chime.com",         ["san francisco", "remote"], "startup"),
    ("Nerdio",        "nerdio.com",        ["chicago", "remote"], "startup"),
    ("Weights & Biases", "wandb.ai",       ["san francisco", "remote"], "startup"),
    ("Pinecone",      "pinecone.io",       ["san francisco", "new york", "remote"], "startup"),
    ("Weaviate",      "weaviate.io",       ["san francisco", "amsterdam", "remote"], "startup"),
    ("Milvus",        "zilliz.com",        ["san francisco", "remote"], "startup"),
    ("LangChain",     "langchain.com",     ["san francisco", "remote"], "startup"),
    ("Replit",        "replit.com",        ["san francisco", "remote"], "startup"),
    ("GitHub",        "github.com",        ["san francisco", "new york", "remote"], "startup"),
    ("GitLab",        "gitlab.com",        ["san francisco", "remote"], "startup"),
    ("Postman",       "postman.com",       ["san francisco", "new york", "bangalore", "remote"], "startup"),
    ("Sentry",        "sentry.io",         ["san francisco", "remote"], "startup"),
    ("LaunchDarkly",  "launchdarkly.com",  ["san francisco", "remote"], "startup"),
    ("Snyk",          "snyk.io",           ["san francisco", "new york", "london", "remote"], "startup"),
    ("Wiz",           "wiz.io",            ["new york", "san francisco", "london", "remote"], "startup"),
    ("Lacework",      "lacework.com",      ["san francisco", "remote"], "startup"),
    ("Orca Security", "orca.security",     ["san francisco", "new york", "remote"], "startup"),
    ("Abnormal Security", "abnormalsecurity.com", ["san francisco", "remote"], "startup"),
    ("Figma",         "figma.com",         ["san francisco", "new york", "remote"], "startup"),
    ("Miro",          "miro.com",          ["san francisco", "amsterdam", "london", "remote"], "startup"),
    ("Lark",          "larksuite.com",     ["san francisco", "singapore", "remote"], "startup"),
    ("Asana",         "asana.com",         ["san francisco", "new york", "london", "remote"], "startup"),
    ("ClickUp",       "clickup.com",       ["san francisco", "new york", "remote"], "startup"),
    ("Monday.com",    "monday.com",        ["new york", "san francisco", "london", "tel aviv", "remote"], "startup"),
    ("Coda",          "coda.io",           ["san francisco", "remote"], "startup"),
    ("Roam Research", "roamresearch.com",  ["remote"], "startup"),
    ("Obsidian",      "obsidian.md",       ["remote"], "startup"),
    ("Amplitude",     "amplitude.com",     ["san francisco", "new york", "remote"], "startup"),
    ("Mixpanel",      "mixpanel.com",      ["san francisco", "new york", "remote"], "startup"),
    ("Segment",       "segment.com",       ["san francisco", "new york", "remote"], "startup"),
    ("dbt Labs",      "getdbt.com",        ["san francisco", "new york", "remote"], "startup"),
    ("Airbyte",       "airbyte.com",       ["san francisco", "remote"], "startup"),
    ("Fivetran",      "fivetran.com",      ["san francisco", "new york", "remote"], "startup"),
    ("Starburst",     "starburst.io",      ["boston", "san francisco", "remote"], "startup"),
    ("SingleStore",   "singlestore.com",   ["san francisco", "remote"], "startup"),
    ("CockroachDB",   "cockroachlabs.com", ["new york", "san francisco", "remote"], "startup"),
    ("MotherDuck",    "motherduck.com",    ["san francisco", "remote"], "startup"),
    ("Neon",          "neon.tech",         ["san francisco", "remote"], "startup"),
    ("PlanetScale",   "planetscale.com",   ["san francisco", "remote"], "startup"),
    ("Temporal",      "temporal.io",       ["san francisco", "remote"], "startup"),
    ("Camunda",       "camunda.com",       ["san francisco", "berlin", "remote"], "startup"),

    # ── Quant / HFT Firms ─────────────────────────────────────────────────────
    ("Jane Street",          "janestreet.com",        ["new york", "london", "hong kong", "singapore"], "quant"),
    ("Two Sigma",            "twosigma.com",           ["new york", "london", "hong kong"], "quant"),
    ("D.E. Shaw",            "deshaw.com",             ["new york", "london", "bangalore", "hyderabad"], "quant"),
    ("Renaissance Technologies", "rentec.com",         ["new york"], "quant"),
    ("Citadel",              "citadel.com",            ["chicago", "new york", "london", "singapore"], "quant"),
    ("Citadel Securities",   "citadelsecurities.com",  ["chicago", "new york", "london", "singapore"], "quant"),
    ("Virtu Financial",      "virtu.com",              ["new york", "london", "singapore"], "quant"),
    ("Jump Trading",         "jumptrading.com",        ["chicago", "new york", "london", "singapore", "amsterdam"], "quant"),
    ("Optiver",              "optiver.com",            ["chicago", "new york", "amsterdam", "london", "singapore"], "quant"),
    ("IMC Trading",          "imc.com",                ["chicago", "new york", "amsterdam", "london", "singapore"], "quant"),
    ("Flow Traders",         "flowtraders.com",        ["new york", "amsterdam", "london", "singapore"], "quant"),
    ("Akuna Capital",        "akunacapital.com",       ["chicago", "boston", "new york", "london", "singapore", "austin"], "quant"),
    ("Hudson River Trading", "hudsonrivertrading.com", ["new york", "london", "singapore"], "quant"),
    ("DRW",                  "drw.com",                ["chicago", "new york", "london", "singapore"], "quant"),
    ("Susquehanna International Group", "sig.com",    ["philadelphia", "new york", "london", "singapore"], "quant"),
    ("Tower Research Capital", "tower-research.com",  ["new york", "london", "singapore"], "quant"),
    ("Millennium Management", "mlp.com",              ["new york", "london", "hong kong"], "quant"),
    ("Point72",              "point72.com",            ["new york", "london", "hong kong", "singapore"], "quant"),
    ("AQR Capital",          "aqr.com",                ["greenwich", "new york", "london"], "quant"),
    ("WorldQuant",           "worldquant.com",         ["new york", "london", "singapore", "remote"], "quant"),
    ("Man Group",            "man.com",                ["london", "new york", "hong kong", "singapore"], "quant"),
    ("Winton Group",         "winton.com",             ["london", "new york", "hong kong"], "quant"),
    ("GS Quantitative Finance", "goldmansachs.com",   ["new york", "london", "bangalore", "singapore"], "quant"),
    ("Squarepoint Capital",  "squarepoint-cap.com",   ["new york", "london", "singapore"], "quant"),
    ("Marshall Wace",        "mwam.com",               ["london", "new york", "singapore"], "quant"),
    ("Balyasny Asset Management", "bamfunds.com",     ["chicago", "new york", "london"], "quant"),
    ("Bluecrest Capital",    "bluecrestcapital.com",  ["london", "new york"], "quant"),
    ("Arrowstreet Capital",  "arrowstreetcapital.com",["boston"], "quant"),
    ("Numeric",              "numeric.com",            ["boston"], "quant"),
    ("AlphaSimplex",         "alphasimplex.com",       ["boston"], "quant"),
    ("PDT Partners",         "pdtpartners.com",        ["new york"], "quant"),
    ("Cubist Systematic Strategies", "cubistsys.com", ["new york", "london"], "quant"),
    ("Qube Research",        "qube-rt.com",            ["london", "hong kong", "singapore"], "quant"),
    ("G-Research",           "gresearch.co.uk",        ["london"], "quant"),

    # ── Trading / Prop Trading / Brokerages ───────────────────────────────────
    ("Interactive Brokers",  "interactivebrokers.com", ["new york", "chicago", "london", "singapore"], "trading"),
    ("Robinhood",            "robinhood.com",           ["san francisco", "new york", "remote"], "trading"),
    ("TD Ameritrade",        "tdameritrade.com",        ["chicago", "new york"], "trading"),
    ("Charles Schwab",       "schwab.com",              ["san francisco", "chicago", "new york", "austin", "remote"], "trading"),
    ("Fidelity Investments", "fidelity.com",            ["boston", "new york", "chicago", "remote"], "trading"),
    ("Vanguard",             "vanguard.com",            ["philadelphia", "new york"], "trading"),
    ("BlackRock",            "blackrock.com",           ["new york", "london", "san francisco", "singapore"], "trading"),
    ("Goldman Sachs",        "goldmansachs.com",        ["new york", "london", "bangalore", "singapore", "salt lake city"], "trading"),
    ("JPMorgan Chase",       "jpmorgan.com",            ["new york", "london", "bangalore", "singapore", "chicago"], "trading"),
    ("Morgan Stanley",       "morganstanley.com",       ["new york", "london", "bangalore", "singapore"], "trading"),
    ("Citi",                 "citi.com",                ["new york", "london", "bangalore", "singapore"], "trading"),
    ("Deutsche Bank",        "db.com",                  ["new york", "london", "frankfurt", "singapore"], "trading"),
    ("UBS",                  "ubs.com",                 ["new york", "london", "zurich", "singapore"], "trading"),
    ("Credit Suisse",        "credit-suisse.com",       ["new york", "london", "zurich", "singapore"], "trading"),
    ("Barclays",             "barclays.com",            ["london", "new york", "singapore"], "trading"),
    ("HSBC",                 "hsbc.com",                ["london", "new york", "hong kong", "singapore"], "trading"),
    ("Nomura",               "nomura.com",              ["new york", "london", "tokyo", "singapore"], "trading"),
    ("Mizuho",               "mizuho-fg.com",           ["new york", "london", "tokyo", "singapore"], "trading"),
    ("BNP Paribas",          "bnpparibas.com",          ["new york", "london", "paris", "singapore"], "trading"),
    ("Societe Generale",     "societegenerale.com",     ["new york", "london", "paris", "singapore"], "trading"),
    ("Natixis",              "natixis.com",             ["new york", "london", "paris"], "trading"),
    ("Piper Sandler",        "pipersandler.com",        ["new york", "chicago", "remote"], "trading"),
    ("Cowen",                "cowen.com",               ["new york", "boston", "london"], "trading"),
    ("Stifel",               "stifel.com",              ["new york", "chicago", "remote"], "trading"),
    ("Raymond James",        "raymondjames.com",        ["new york", "chicago", "remote"], "trading"),
    ("Susquehanna International Group", "sig.com",    ["philadelphia", "new york", "chicago"], "trading"),

    # ── Fintech ───────────────────────────────────────────────────────────────
    ("PayPal",         "paypal.com",      ["san francisco", "new york", "chicago", "austin", "london", "remote"], "fintech"),
    ("Square",         "squareup.com",    ["san francisco", "new york", "remote"], "fintech"),
    ("Block",          "block.xyz",       ["san francisco", "new york", "remote"], "fintech"),
    ("Affirm",         "affirm.com",      ["san francisco", "new york", "remote"], "fintech"),
    ("Klarna",         "klarna.com",      ["new york", "san francisco", "london", "stockholm", "remote"], "fintech"),
    ("Adyen",          "adyen.com",       ["san francisco", "new york", "chicago", "london", "amsterdam", "singapore"], "fintech"),
    ("Checkout.com",   "checkout.com",    ["san francisco", "new york", "london", "remote"], "fintech"),
    ("Marqeta",        "marqeta.com",     ["san francisco", "remote"], "fintech"),
    ("Navan",          "navan.com",       ["san francisco", "new york", "london", "remote"], "fintech"),
    ("Divvy",          "divvy.co",        ["salt lake city", "remote"], "fintech"),
    ("Varo Bank",      "varomoney.com",   ["san francisco", "remote"], "fintech"),
    ("Current",        "current.com",     ["new york", "remote"], "fintech"),
    ("Dave",           "dave.com",        ["los angeles", "remote"], "fintech"),
    ("Betterment",     "betterment.com",  ["new york", "remote"], "fintech"),
    ("Wealthfront",    "wealthfront.com", ["san francisco", "remote"], "fintech"),
    ("SoFi",           "sofi.com",        ["san francisco", "new york", "remote"], "fintech"),
    ("LendingClub",    "lendingclub.com", ["san francisco", "remote"], "fintech"),
    ("Avant",          "avant.com",       ["chicago", "remote"], "fintech"),
    ("Blend",          "blend.com",       ["san francisco", "remote"], "fintech"),
    ("Opendoor",       "opendoor.com",    ["san francisco", "new york", "remote"], "fintech"),
    ("Divvy Homes",    "divvyhomes.com",  ["san francisco", "remote"], "fintech"),
]


def normalize_location(location: str) -> str:
    """Return canonical location key or original lowercased value."""
    loc_lower = location.strip().lower()
    for canonical, aliases in LOCATION_ALIASES.items():
        if loc_lower in aliases:
            return canonical
    return loc_lower


def get_companies_for_location(
    locations: list[str],
    categories: list[str] | None = None,
) -> list[dict]:
    """
    Return companies that operate in any of the requested locations.

    Parameters
    ----------
    locations:
        List of location strings provided by the user (e.g. ["New York", "Remote"]).
        Pass ["any"] or an empty list to return all companies.
    categories:
        Subset of {"big_tech","startup","quant","trading","fintech"}.
        None / empty = all categories.
    """
    want_any = not locations or locations == ["any"]
    normalized_wanted = [normalize_location(l) for l in locations] if not want_any else []

    # expand aliases so user input matches db entries
    expanded_wanted: set[str] = set()
    for w in normalized_wanted:
        expanded_wanted.add(w)
        if w in LOCATION_ALIASES:
            expanded_wanted.update(LOCATION_ALIASES[w])

    seen_domains: set[str] = set()
    results: list[dict] = []

    for name, domain, comp_locations, category in COMPANIES_DB:
        if domain in seen_domains:
            continue
        if categories and category not in categories:
            continue

        if want_any:
            match = True
        else:
            # check if company is in any wanted location or is remote
            comp_locs_expanded: set[str] = set()
            for cl in comp_locations:
                comp_locs_expanded.add(cl)
                if cl in LOCATION_ALIASES:
                    comp_locs_expanded.update(LOCATION_ALIASES[cl])
            # "remote" companies match everywhere
            match = bool(comp_locs_expanded & expanded_wanted) or "remote" in comp_locations

        if match:
            seen_domains.add(domain)
            results.append({
                "name": name,
                "domain": domain,
                "career_url": "",
                "category": category,
                "locations": comp_locations,
            })

    return results
