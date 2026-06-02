import pandas as pd
from django.shortcuts import render
from django.http import HttpResponse
from google_play_scraper import search
import requests
from bs4 import BeautifulSoup
import io


def search_apps(request):
    results = []
    keyword = ''
    # Default values set ki hain
    min_installs = 500
    max_installs = 5000

    if request.method == "POST":
        keyword = request.POST.get('keyword', '').strip()
        # Input se values li hain
        min_installs = int(request.POST.get('min_installs', 500))
        max_installs = int(request.POST.get('max_installs', 5000))

        if keyword:
            try:
                # n_hits 10 se badhakar 30 kar di hai taaki filter hone par bhi results milein
                apps = search(keyword, lang="en", country="in", n_hits=30)

                for app in apps:
                    installs_str = app.get('installs', '0').replace(',', '').replace('+', '')
                    installs_count = int(installs_str) if installs_str.isdigit() else 0

                    # Dynamic Range Filter
                    if min_installs <= installs_count <= max_installs:
                        url = f"https://play.google.com/store/apps/details?id={app['appId']}"
                        data_row = {
                            'title': app.get('title'),
                            'appId': app['appId'],
                            'installs': app.get('installs'),
                            'score': app.get('score', 0),
                            'email': 'N/A',
                            'website': 'N/A',
                            'phone': 'N/A'
                        }

                        try:
                            headers = {'User-Agent': 'Mozilla/5.0'}
                            resp = requests.get(url, headers=headers, timeout=5)
                            if resp.status_code == 200:
                                soup = BeautifulSoup(resp.content, 'html.parser')
                                email_tag = soup.find('a', href=lambda x: x and x.startswith('mailto:'))
                                if email_tag:
                                    data_row['email'] = email_tag['href'].replace('mailto:', '').split('?')[0]
                                web_tag = soup.find('a', {'aria-label': lambda x: x and 'website' in x.lower()})
                                if web_tag and web_tag.has_attr('href'):
                                    data_row['website'] = web_tag['href'].split('//')[-1].split('/')[0]
                        except Exception:
                            pass
                        results.append(data_row)

                # Session mein save kiya taki download button kaam kare
                request.session['search_data'] = results

            except Exception as e:
                print(f"Scraping Error: {e}")

    return render(request, 'index.html', {
        'results': results,
        'keyword': keyword,
        'min_installs': min_installs,
        'max_installs': max_installs
    })


def download_excel(request):
    data = request.session.get('search_data')
    if not data:
        return HttpResponse("No data to download.")

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)

    response = HttpResponse(output.read(), content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename="apps.xlsx"'
    return response