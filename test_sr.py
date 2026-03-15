import cloudscraper
import pandas as pd
from io import StringIO
scraper = cloudscraper.create_scraper()
html = scraper.get('https://www.sports-reference.com/cbb/seasons/men/2025-advanced-school-stats.html').text
dfs = pd.read_html(StringIO(html))
print(dfs[0].head())
