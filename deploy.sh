#!/usr/bin/env bash
# deploy.sh — publish the reviewed site to the live droplet.
#
#   ./deploy.sh              dry run: list exactly what would change
#   ./deploy.sh --apply      publish
#
# Read-only by default, per the poplab house rule. Run this ON quasimodo:
# pop-os has no route to the droplet, quasimodo reaches it as `clawfirm-droplet`.
#
# Never uses --delete. The docroot is shared nginx territory and holds files this
# tree does not know about; making the destination match the source would remove
# them.
set -o errexit -o nounset -o pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="clawfirm-droplet"
DEST="/var/www/appearance-unlimited.com"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

# Site content only. Dev files, the catalog source and build tooling stay home.
EXCLUDES=(--exclude 'README.md' --exclude '_template.html' --exclude 'start-server.sh'
          --exclude 'deploy.sh' --exclude '.git' --exclude 'assets/img/au2.png'
          --exclude 'scripts' --exclude 'assets/data' --exclude 'projects'
          --exclude 'assets/img/merch/src-*.png')

echo "==> $SRC  ->  $HOST:$DEST"
if [[ $APPLY -eq 0 ]]; then
  echo "==> DRY RUN (pass --apply to publish)"
  rsync -avn --no-perms --no-owner --no-group "${EXCLUDES[@]}" "$SRC/" "$HOST:$DEST/"
  echo
  echo "Nothing was changed. Re-run with --apply to publish."
  exit 0
fi

rsync -av --no-perms --no-owner --no-group "${EXCLUDES[@]}" "$SRC/" "$HOST:$DEST/"

# nginx serves as www-data; rsync ran as root, so hand ownership back.
ssh "$HOST" "chown -R www-data:www-data $DEST && find $DEST -type d -exec chmod 755 {} + && find $DEST -type f -exec chmod 644 {} +"

echo
echo "==> verifying over HTTPS"
for p in index services about portfolio merch merch-au-car-logo-mug; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "https://appearance-unlimited.com/$p.html")
  n=$(curl -s "https://appearance-unlimited.com/$p.html" | grep -c has-photo || true)
  m=$(curl -s "https://appearance-unlimited.com/$p.html" | grep -c merch-card || true)
  printf '    %-26s %s  frames=%s merch-cards=%s\n' "$p.html" "$code" "$n" "$m"
done
echo
echo "Expected: 200 everywhere; frames 10/5/7/16 on the first four; merch shows 20+ cards."
