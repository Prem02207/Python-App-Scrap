import pandas as pd
from django.shortcuts import render
from django.http import HttpResponse
from google_play_scraper import search, app
import requests
from bs4 import BeautifulSoup
import io
import re
from django.views.decorators.csrf import csrf_exempt

COUNTRIES = [
    ("all", "All"), ("in", "India"), ("np", "Nepal"), ("lk", "Sri Lanka"),
    ("cn", "China"), ("nz", "New Zealand"), ("za", "South Africa"), ("us", "USA"),
    ("gb", "UK"), ("de", "Germany"), ("au", "Australia"), ("fr", "France"), ("ae", "UAE")
]

CATEGORIES = [
    ("GAME", "Games"), ("FINANCE", "Finance"), ("BUSINESS", "Business"),
    ("TOOLS", "Tools"), ("EDUCATION", "Education"), ("ENTERTAINMENT", "Entertainment"),
    ("SOCIAL", "Social"), ("SHOPPING", "Shopping"), ("HEALTH", "Health"),
    ("SOFTWARE", "Software"), ("FINTECH", "Fintech"), ("DEVELOPMENT", "Development"),
    ("DESIGN", "Design"), ("SALES", "Sales")
]


@csrf_exempt
def search_apps(request):
    results = []
    keyword, selected_country, selected_cat, selected_year = '', 'all', 'All', 'All'
    min_installs, max_installs = '1', '10000000'
    years = list(range(2028, 1999, -1))

    if request.method == "POST":
        keyword = request.POST.get('keyword', '').strip()
        selected_country = request.POST.get('country', 'all')
        selected_cat = request.POST.get('category', 'All')
        selected_year = request.POST.get('year', 'All')
        min_installs = request.POST.get('min_installs', '1')
        max_installs = request.POST.get('max_installs', '10000000')

        if keyword:
            try:
                min_i, max_i = int(min_installs), int(max_installs)
                search_country = 'us' if selected_country == 'all' else selected_country

                apps = search(keyword, lang="en", country=search_country, n_hits=40)

                for item in apps:
                    try:
                        details = app(item['appId'], lang='en', country=search_country)
                        raw_installs = details.get('installs', '0').replace(',', '').replace('+', '')
                        curr_installs = int(raw_installs) if raw_installs.isdigit() else 0

                        if not (min_i <= curr_installs <= max_i): continue

                        rel_date = details.get('released', '')
                        app_year = rel_date.split(', ')[-1] if ', ' in rel_date else 'N/A'
                        app_genre = details.get('genre', '').upper()

                        if (selected_year != 'All' and selected_year != app_year) or \
                                (selected_cat != 'All' and selected_cat.upper() not in app_genre): continue

                        url = f"https://play.google.com/store/apps/details?id={item['appId']}"
                        resp = requests.get(url, timeout=5)
                        soup = BeautifulSoup(resp.content, 'html.parser')
                        phone_pattern = re.compile(r'(\+\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}')
                        phone_match = phone_pattern.search(soup.get_text())
                        web_tag = soup.find('a', {'aria-label': lambda x: x and 'website' in x.lower()})

                        results.append({
                            'appId': item['appId'],
                            'title': details.get('title', 'N/A'), 'icon': details.get('icon', ''),
                            'email': details.get('developerEmail', 'N/A'),
                            'phone': phone_match.group() if phone_match else "N/A",
                            'website': web_tag['href'] if web_tag and web_tag.has_attr('href') else "N/A",
                            'year': app_year, 'installs': details.get('installs', '0')
                        })
                    except:
                        continue
                request.session['search_data'] = results
            except Exception as e:
                print(e)

    return render(request, 'index.html', {
        'results': results, 'categories': CATEGORIES, 'countries': COUNTRIES, 'years': years,
        'keyword': keyword, 'selected_cat': selected_cat, 'selected_country': selected_country,
        'selected_year': selected_year, 'min_installs': min_installs, 'max_installs': max_installs
    })


def download_excel(request):
    data = request.session.get('search_data')
    if not data: return HttpResponse("No data.")
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer: df.to_excel(writer, index=False)
    output.seek(0)
    response = HttpResponse(output.read(),
                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="apps_data.xlsx"'
    return response