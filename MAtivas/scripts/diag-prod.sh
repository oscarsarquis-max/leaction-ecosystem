#!/bin/bash
grep -oh 'localhost:[0-9]*' /usr/share/nginx/html/assets/*.js 2>/dev/null | sort -u
grep -oh 'https://metodologiasinovativas[^"]*' /usr/share/nginx/html/assets/*.js 2>/dev/null | sort -u
curl -sk -X POST https://metodologiasinovativas.com.br/api/admin/login -H 'Content-Type: application/json' -d '{"password":"InovAtivas2026!"}'
echo
curl -sk -X POST https://metodologiasinovativas.com.br/api/admin/login -H 'Content-Type: application/json' -d '{"password":"admin123"}'
echo
curl -sk -X POST https://metodologiasinovativas.com.br/api/admin/login -H 'Content-Type: application/json' -d '{"password":"wrong"}'
echo
