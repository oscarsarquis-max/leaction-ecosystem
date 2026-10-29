set -e
echo '=== BEFORE ==='
df -h /
df -h /var/www /home/ubuntu 2>/dev/null || true
du -sh /var/www/leaction-platform/* 2>/dev/null | sort -hr | head -20
du -sh /home/ubuntu/.npm /tmp /var/log 2>/dev/null || true
echo '=== CLEAN ==='
# npm caches
npm cache clean --force 2>/dev/null || true
rm -rf /home/ubuntu/.npm/_cacache /home/ubuntu/.npm/_logs 2>/dev/null || true
# leftover next/node_modules build junk in /tmp
rm -rf /tmp/* 2>/dev/null || true
# old deploy zip leftovers
rm -f /tmp/leaction-platform-deploy.zip /tmp/cms-promote-*.sh 2>/dev/null || true
# journal vacuum
sudo journalctl --vacuum-size=50M 2>/dev/null || true
# apt
sudo apt-get clean 2>/dev/null || true
# if node_modules half-written, remove for clean reinstall (pm2 still on old process memory)
# Keep running services; only clear incomplete frontend node_modules if huge
du -sh /var/www/leaction-platform/frontend/action-hub/node_modules 2>/dev/null || true
du -sh /var/www/leaction-platform/frontend/action-hub/.next 2>/dev/null || true
echo '=== AFTER ==='
df -h /