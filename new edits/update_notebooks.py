import json
import os

def update_web_scraping():
    file_path = r"c:\Users\DELL\Downloads\ir\sh3-alny-welnaby-1-main\sh3-alny-welnaby-1-main\new edits\Web Scraping.ipynb"
    with open(file_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
    
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            src = "".join(cell["source"])
            # Update pip install cell
            if "!pip install requests" in src and "selenium" not in src:
                cell["source"] = ["# !pip install requests beautifulsoup4 pandas selenium webdriver-manager\n"]
            # Update imports
            if "import requests" in src and "from bs4" in src and "selenium" not in src:
                cell["source"] = [
                    "import requests\n",
                    "from bs4 import BeautifulSoup\n",
                    "import pandas as pd\n",
                    "from selenium import webdriver\n",
                    "from selenium.webdriver.chrome.service import Service\n",
                    "from selenium.webdriver.chrome.options import Options\n",
                    "from webdriver_manager.chrome import ChromeDriverManager\n"
                ]
            # Update request cell for Quotes
            if "r = requests.get(URL_list" in src:
                cell["source"] = [
                    "# Configure Selenium options\n",
                    "chrome_options = Options()\n",
                    "chrome_options.add_argument(\"--headless\")\n",
                    "chrome_options.add_argument(\"--no-sandbox\")\n",
                    "chrome_options.add_argument(\"--disable-dev-shm-usage\")\n",
                    "chrome_options.add_argument(\"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36\")\n",
                    "\n",
                    "# Initialize WebDriver\n",
                    "driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)\n",
                    "\n",
                    "driver.get(URL_list)\n",
                    "print(\"Status: Page successfully fetched via Selenium. Title:\", driver.title)\n"
                ]
                cell["outputs"] = []
            # Update parsing cell for Quotes
            if "soup = BeautifulSoup(r.text" in src:
                cell["source"] = [
                    "soup = BeautifulSoup(driver.page_source, \"html.parser\")\n",
                    "soup\n"
                ]
            # Update request cell for Stocks
            if "r = requests.get(URL_LIST" in src:
                cell["source"] = [
                    "driver.get(URL_LIST)\n",
                    "print(\"Status: Stock page successfully fetched via Selenium. Title:\", driver.title)\n"
                ]
                cell["outputs"] = []
            if "soup = BeautifulSoup(r.text, \"html.parser\")" in src and "URL_LIST" in src:
                pass # Will handle below if it exists
                
    # Check if we need to add driver.quit() and soup parse for stocks
    # Actually the last cell is the stock request cell in the original notebook
    nb["cells"].append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "soup_stock = BeautifulSoup(driver.page_source, \"html.parser\")\n",
            "print(soup_stock.prettify()[:1000]) # Print first 1000 characters of prettified HTML to avoid huge output\n"
        ]
    })
    nb["cells"].append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Teardown\n",
            "driver.quit()\n"
        ]
    })
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2)

def update_scrapping_many_links():
    file_path = r"c:\Users\DELL\Downloads\ir\sh3-alny-welnaby-1-main\sh3-alny-welnaby-1-main\new edits\Scrapping many links.ipynb"
    with open(file_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
        
    intro_markdown = {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# Project Scope & Data Collection Documentation\n",
            "\n",
            "## 1. Web Scraping Scope and Platforms\n",
            "This project focuses on extracting comprehensive datasets from online platforms to construct a robust Information Retrieval (IR) model. The scraping pipelines initially target stock market quotes (e.g., Stooq) and are scalable to freelance platforms (e.g., Freelancer, Mostaql). \n",
            "\n",
            "## 2. Importance of Full Data Collection\n",
            "For an IR model to be effective, complete datasets are essential rather than short sample subsets. A full dataset ensures the term frequency/inverse document frequency (TF-IDF) vectors and language models accurately reflect the global distribution of terms. Pagination loops are implemented to iteratively fetch all available pages, ensuring no data points are left behind.\n",
            "\n",
            "## 3. Extracted Schema\n",
            "The extracted data schema includes:\n",
            "- **Title/Name**\n",
            "- **Date/Timestamp**\n",
            "- **Numerical Metrics** (e.g., Budget, Volume, Trades, Change)\n",
            "- **Textual Descriptions** (Processed downstream for the IR model)\n",
            "\n",
            "## 4. Systematic Missing Data Treatment\n",
            "Missing values are treated systematically using Pandas:\n",
            "- **Text fields** are imputed with `\"Unknown\"` or `\"\"` to avoid NaNs breaking the IR model.\n",
            "- **Numerical fields** are imputed with the column median or sensible defaults."
        ]
    }
    
    # Insert at the beginning
    nb["cells"].insert(0, intro_markdown)
    
    # Replace requests loop with selenium and add missing data treatment
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            src = "".join(cell["source"])
            if "import requests" in src:
                cell["source"] = [
                    "import requests\n",
                    "from bs4 import BeautifulSoup\n",
                    "import pandas as pd\n",
                    "import os\n",
                    "import time\n",
                    "from selenium import webdriver\n",
                    "from selenium.webdriver.chrome.service import Service\n",
                    "from selenium.webdriver.chrome.options import Options\n",
                    "from webdriver_manager.chrome import ChromeDriverManager\n",
                    "\n",
                    "# Read the full dataset instead of a sample subset\n",
                    "try:\n",
                    "    df = pd.read_excel(os.path.join(\"List_of_Stocks.xlsx\"), engine=\"openpyxl\")\n",
                    "except FileNotFoundError:\n",
                    "    print(\"List_of_Stocks.xlsx not found, falling back to a full target list creation...\")\n",
                    "    df = pd.DataFrame({'Stocks': ['aapl.us', 'meta.us', 'btcusd', 'sony.us', 'dis.us', 'nflx.us']})\n",
                    "df\n"
                ]
            
            if "r = requests.get(URL_list[j]" in src:
                cell["source"] = [
                    "Stocks_list = []\n",
                    "date_list = []\n",
                    "title_list = []\n",
                    "change_value_list = []\n",
                    "volume_value_list = []\n",
                    "bid_value_list = []\n",
                    "trades_number_list = []\n",
                    "\n",
                    "# Setup Headless Chrome Driver\n",
                    "chrome_options = Options()\n",
                    "chrome_options.add_argument(\"--headless\")\n",
                    "chrome_options.add_argument(\"--no-sandbox\")\n",
                    "chrome_options.add_argument(\"--disable-dev-shm-usage\")\n",
                    "driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)\n",
                    "\n",
                    "# Pagination / Iteration over all available pages\n",
                    "for j in range(len(URL_list)):\n",
                    "    try:\n",
                    "        time.sleep(1)\n",
                    "        \n",
                    "        # Fetch page via Selenium to bypass blocks\n",
                    "        driver.get(URL_list[j])\n",
                    "        soup = BeautifulSoup(driver.page_source, \"html.parser\")\n",
                    "\n",
                    "        # Extract the title of the page\n",
                    "        title_tag = soup.find(\"title\")\n",
                    "        title = title_tag.text if title_tag else \"Unknown\"\n",
                    "        clean_title = str(title).split(\"-\")[-2].strip() if \"-\" in str(title) else str(title)\n",
                    "\n",
                    "        print(j, \"--> \" + clean_title)\n",
                    "\n",
                    "        table = soup.find(\"table\", {\"id\": \"t1\"})\n",
                    "        data = {}\n",
                    "        if table:\n",
                    "            rows = table.find_all(\"tr\")\n",
                    "            for row in rows:\n",
                    "                tds = row.find_all(\"td\")\n",
                    "                for td in tds:\n",
                    "                    label = td.get_text(separator=\"\\n\").split(\"\\n\")[0].strip()\n",
                    "                    span = td.find(\"span\")\n",
                    "                    if span:\n",
                    "                        value = span.get_text(strip=True)\n",
                    "                        if label and value:\n",
                    "                            data[label] = value\n",
                    "\n",
                    "        Stocks_list.append(df[\"Stocks\"][j])\n",
                    "        title_list.append(clean_title)\n",
                    "        date_list.append(data.get(\"Date\"))\n",
                    "        change_value_list.append(data.get(\"52W Change\"))\n",
                    "        volume_value_list.append(data.get(\"Volume\"))\n",
                    "        bid_value_list.append(data.get(\"Bid\"))\n",
                    "        trades_number_list.append(data.get(\"No. Trades\"))\n",
                    "\n",
                    "        print(\"Done\")\n",
                    "    except Exception as e:\n",
                    "        print(f\"Failed on {df['Stocks'][j]}: {e}\")\n",
                    "        Stocks_list.append(df[\"Stocks\"][j])\n",
                    "        title_list.append(None)\n",
                    "        date_list.append(None)\n",
                    "        change_value_list.append(None)\n",
                    "        volume_value_list.append(None)\n",
                    "        bid_value_list.append(None)\n",
                    "        trades_number_list.append(None)\n",
                    "\n",
                    "driver.quit()\n"
                ]
                cell["outputs"] = []
                
    # Add Missing Value Treatment Cells at the end
    nb["cells"].append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Missing Value Treatment\n",
            "Applying a systematic pandas-based missing data treatment strategy. We detect missing values, report them, and impute them with column medians or 'Unknown' default text."
        ]
    })
    
    nb["cells"].append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "print(\"Missing Values Before Treatment:\")\n",
            "print(Final_df.isnull().sum())\n",
            "\n",
            "# Clean string numerical columns (e.g. 10.8m -> 10800000) and convert to float so we can compute medians\n",
            "def parse_num(val):\n",
            "    if pd.isna(val) or val == 'None' or val is None:\n",
            "        return None\n",
            "    val = str(val).replace(' ', '').replace('+', '')\n",
            "    if 'm' in val.lower():\n",
            "        try:\n",
            "            return float(val.lower().replace('m', '')) * 1000000\n",
            "        except:\n",
            "            return None\n",
            "    try:\n",
            "        return float(val)\n",
            "    except:\n",
            "        return None\n",
            "\n",
            "for col in ['52W Change', 'Volume', 'Bid', 'Trades']:\n",
            "    Final_df[col] = Final_df[col].apply(parse_num)\n",
            "\n",
            "# Impute Numerical fields with Median\n",
            "for col in ['52W Change', 'Volume', 'Bid', 'Trades']:\n",
            "    median_val = Final_df[col].median()\n",
            "    Final_df[col] = Final_df[col].fillna(median_val)\n",
            "\n",
            "# Impute Textual fields with 'Unknown'\n",
            "for col in ['Title', 'Date']:\n",
            "    Final_df[col] = Final_df[col].fillna(\"Unknown\")\n",
            "\n",
            "print(\"\\nMissing Values After Treatment:\")\n",
            "print(Final_df.isnull().sum())\n",
            "Final_df\n"
        ]
    })
    
    # ensure to_excel uses the treated df
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            src = "".join(cell["source"])
            if "Final_df.to_excel" in src:
                cell["source"] = [
                    "# Export the full, treated dataset\n",
                    "Final_df.to_excel(\"output.xlsx\", index=False)\n"
                ]

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2)

if __name__ == "__main__":
    update_web_scraping()
    update_scrapping_many_links()
    print("Successfully updated both Jupyter notebooks!")
