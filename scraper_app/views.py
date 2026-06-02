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
    min_installs = 100
    max_installs = 10000000

    if request.method == "POST":
        keyword = request.POST.get('keyword', '').strip()
        try:
            min_installs = int(request.POST.get('min_installs', 100))
            max_installs = int(request.POST.get('max_installs', 10000000))
        except:
            pass

        if keyword:
            try:
                # n_hits 10 rakhein taaki server par load kam ho
                apps = search(keyword, lang="en", country="in", n_hits=10)

                for app in apps:
                    installs_str = str(app.get('installs', '0')).replace(',', '').replace('+', '')
                    installs_count = int(installs_str) if installs_str.isdigit() else 0

                    if min_installs <= installs_count <= max_installs:
                        data_row = {
                            'title': str(app.get('title', 'N/A')),
                            'appId': str(app.get('appId', 'N/A')),
                            'installs': str(app.get('installs', '0')),
                            'score': str(app.get('score', 0)),
                            'email': 'N/A',
                            'website': 'N/A'
                        }

                        # Scraping sirf tabhi karein jab zaroori ho
                        try:
                            url = f"https://play.google.com/store/apps/details?id={data_row['appId']}"
                            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
                            if resp.status_code == 200:
                                soup = BeautifulSoup(resp.content, 'html.parser')
                                email_tag = soup.find('a', href=lambda x: x and x.startswith('mailto:'))
                                if email_tag:
                                    data_row['email'] = email_tag['href'].replace('mailto:', '').split('?')[0]
                                web_tag = soup.find('a', {'aria-label': lambda x: x and 'website' in x.lower()})
                                if web_tag and web_tag.has_attr('href'):
                                    data_row['website'] = web_tag['href'].split('//')[-1].split('/')[0]
                        except:
                            pass
                        results.append(data_row)

                request.session['search_data'] = results

            except Exception as e:
                print(f"Error: {e}")

    return render(request, 'index.html', {'results': results, 'keyword': keyword, 'min_installs': min_installs, 'max_installs': max_installs})

def download_excel(request):
    data = request.session.get('search_data')
    if not data: return HttpResponse("No data")
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    response = HttpResponse(output.read(), content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename="apps.xlsx"'
    return response