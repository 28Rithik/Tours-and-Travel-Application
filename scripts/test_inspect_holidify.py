import urllib.request
import re
from bs4 import BeautifulSoup

url = 'https://www.holidify.com/packages/south-india-tour-packages-178.html'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
soup = BeautifulSoup(html, 'html.parser')

print('Title:', soup.title.string if soup.title else '')
links = soup.find_all('a', href=lambda h: h and '/tour-package/' in h)
print('Total /tour-package/ links:', len(links))
unique_links = list(dict.fromkeys([a['href'] for a in links]))
print('Unique /tour-package/ links:', len(unique_links))
for l in unique_links[:10]:
    print(' ', l)

# Let's check the container around each link
if links:
    parent = links[0]
    for _ in range(5):
        parent = parent.parent
    print('\nSnippet of card parent:')
    print(parent.prettify()[:600])
