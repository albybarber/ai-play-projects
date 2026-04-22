const { execSync } = require('child_process')
const fs = require('fs')
const path = require('path')

const PLUGIN_DEST = '/Library/CoreMediaIO/Plug-Ins/DAL/VideoOverlayCamera.plugin'
// During development the built plugin lives next to this repo
const PLUGIN_SRC = path.join(__dirname, '..', 'plugin', 'build', 'VideoOverlayCamera.plugin')

function isInstalled() {
  return fs.existsSync(PLUGIN_DEST)
}

function install() {
  if (!fs.existsSync(PLUGIN_SRC)) {
    return { ok: false, error: 'Plugin not built. Run: npm run build:plugin' }
  }
  try {
    const script = `do shell script "rm -rf '${PLUGIN_DEST}' && cp -r '${PLUGIN_SRC}' '${PLUGIN_DEST}'" with administrator privileges`
    execSync(`osascript -e '${script}'`, { stdio: 'pipe' })
    return { ok: true }
  } catch (e) {
    return { ok: false, error: e.message }
  }
}

function uninstall() {
  try {
    const script = `do shell script "rm -rf '${PLUGIN_DEST}'" with administrator privileges`
    execSync(`osascript -e '${script}'`, { stdio: 'pipe' })
    return { ok: true }
  } catch (e) {
    return { ok: false, error: e.message }
  }
}

module.exports = { isInstalled, install, uninstall }
