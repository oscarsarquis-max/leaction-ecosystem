const fs = require('fs')
const s = fs.readFileSync('c:/Projetos/MAtivas/frontend/dist/assets/index-BF2OQDCh.js', 'utf8')
const urls = [...new Set(s.match(/https:\/\/[a-z0-9.-]+\.com\.br/g) || [])]
const localhost = [...new Set(s.match(/localhost:\d+/g) || [])]
console.log('prod urls:', urls)
console.log('localhost:', localhost)
