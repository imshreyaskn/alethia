import requests
import re
res = requests.get('https://alethia-gamma.vercel.app/')
js_files = re.findall(r'src=\"(.*?\.js)\"', res.text)
for js in js_files:
    print('Current live JS file:', js)
    js_code = requests.get('https://alethia-gamma.vercel.app' + js).text
    if 'from("pipeline_runs")' in js_code or "from('pipeline_runs')" in js_code:
        print('Found direct Supabase query!')
    if '/api/runs' in js_code:
        print('Found backend /api/runs call!')
