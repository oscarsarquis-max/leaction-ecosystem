import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { renderMediaPlayerMarkup, renderScormH5pMarkup } from './render-player.js'

describe('render-player', () => {
  it('injeta overlay sobre iframe YouTube', () => {
    const html = renderMediaPlayerMarkup({
      mediaUrl: 'https://youtu.be/dQw4w9WgXcQ',
      title: 'T',
      overlays: [{ id: 'n1', atSec: 10, type: 'note', text: 'Nota' }],
      activeOverlayId: 'n1',
    })
    assert.match(html, /player-iframe/)
    assert.match(html, /player-overlay/)
    assert.match(html, /youtube-nocookie/)
  })

  it('renderiza iframe SCORM sandbox', () => {
    const html = renderScormH5pMarkup({
      packageUrl: 'https://cdn.leactiona.local/scorm/index.html',
      kind: 'SCORM',
      title: 'Pacote',
    })
    assert.match(html, /scorm-iframe/)
    assert.match(html, /sandbox=/)
  })
})
