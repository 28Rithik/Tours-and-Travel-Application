import urllib.request
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

def inspect(url):
    print("=" * 80)
    print("URL:", url)
    req = urllib.request.Request(url, headers=HEADERS)
    html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
    soup = BeautifulSoup(html, 'html.parser')
    
    # Check title tag
    print("PAGE TITLE:", soup.title.string.strip() if soup.title else "N/A")
    
    # Check dl
    dl = soup.find('dl')
    if dl:
        # Find all dt and dd
        dts = [dt.get_text(strip=True) for dt in dl.find_all('dt')]
        dds = [dd.get_text(strip=True) for dd in dl.find_all('dd')]
        print(f"DAYS FOUND ({len(dts)}):")
        for dt, dd in zip(dts, dds):
            print(f"  {dt}: {dd}")
            
    # Check surrounding h1, h2, h3, h4, p
    for el in soup.find_all(['header', 'footer', 'nav']):
        el.decompose()
        
    for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5']):
        print(f"HEAD {h.name} [{h.get('class')}]: {h.get_text(strip=True)}")
        
    for p in soup.find_all('p'):
        t = p.get_text(strip=True)
        if len(t) > 20 and not 'cookie' in t.lower():
            print(f"P: {t[:120]}")

if __name__ == '__main__':
    inspect('https://manojtravels.in/packageDetails/1/coimbatore-kodaikanal-coimbatore')
    inspect('https://manojtravels.in/packageDetails/12/navagraha-temple-package-2days')
    inspect('https://manojtravels.in/packageDetails/10/bangalore-mysore-coorg-ooty-kodaikanal-coimbatore')
