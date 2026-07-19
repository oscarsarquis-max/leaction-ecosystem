/**
 * Ditado por voz (Web Speech API) — robusto para sessões longas.
 * Parar: clique em «Parar ditado», no botão do mic ou diga «fim».
 */
(function (global) {
    'use strict';

    var PARADA_RE = /\b(fim|finalizar|encerrar|parar ditado|parar o ditado|stop)\b/i;
    var MAX_REINICIOS_SESSAO = 40;

    function qsa(root, sel) {
        if (typeof root === 'string') root = document.querySelector(root);
        if (!root) return [];
        return Array.from(root.querySelectorAll(sel));
    }

    function PanelDxVozDitado() {
        this.root = document;
        this.statusEl = null;
        this.stopBarEl = null;
        this.onError = null;
        this.sessionAtiva = false;
        this.paradaManual = false;
        this.recebeu = false;
        this.campoAlvo = null;
        this.campoAlvoId = null;
        this.btnAtivo = null;
        this.motor = null;
        this.valorBase = '';
        this.transcricaoSessao = '';
        this._boundClick = null;
        this._restartTimer = null;
        this._startTimer = null;
        this._reiniciosSessao = 0;
        this._iniciandoMotor = false;
    }

    PanelDxVozDitado.prototype.setStatus = function (msg) {
        if (this.statusEl) this.statusEl.textContent = msg || '';
    };

    PanelDxVozDitado.prototype.notifyError = function (msg, critico) {
        if (critico) {
            if (typeof this.onError === 'function') this.onError(msg);
            else if (msg) alert(msg);
        } else if (msg) {
            this.setStatus(msg);
        }
    };

    PanelDxVozDitado.prototype.obterCampo = function (campoId) {
        return campoId ? document.getElementById(campoId) : null;
    };

    PanelDxVozDitado.prototype.processarParadaPorVoz = function (texto) {
        if (!texto) return { stop: false, texto: '' };
        var raw = String(texto).trim();
        var match = raw.match(PARADA_RE);
        if (!match) return { stop: false, texto: raw };
        var idx = raw.toLowerCase().indexOf(match[1].toLowerCase());
        var antes = raw.slice(0, idx).trim().replace(/[,.\-–—;:\s]+$/g, '');
        return { stop: true, texto: antes };
    };

    PanelDxVozDitado.prototype.resetarMic = function (btn) {
        if (!btn) return;
        btn.classList.remove('mic-voz-ouvindo');
        btn.setAttribute('aria-pressed', 'false');
        var label = btn.querySelector('.mic-label');
        if (label) label.textContent = 'Ditado';
        btn.disabled = false;
    };

    PanelDxVozDitado.prototype.resetarTodosMics = function () {
        qsa(this.root, '.btn-voz-campo').forEach(this.resetarMic.bind(this));
        qsa(this.root, 'textarea.ditado-ativo, input.ditado-ativo').forEach(function (el) {
            el.classList.remove('ditado-ativo');
        });
    };

    PanelDxVozDitado.prototype.marcarOuvindo = function (btn, campoId) {
        this.campoAlvoId = campoId;
        this.btnAtivo = btn;
        qsa(this.root, '.btn-voz-campo').forEach(function (b) {
            if (b === btn) {
                b.classList.add('mic-voz-ouvindo');
                b.setAttribute('aria-pressed', 'true');
                var lbl = b.querySelector('.mic-label');
                if (lbl) lbl.textContent = 'Parar';
            } else {
                b.disabled = true;
                this.resetarMic(b);
            }
        }.bind(this));
        qsa(this.root, 'textarea.ditado-ativo, input.ditado-ativo').forEach(function (el) {
            el.classList.remove('ditado-ativo');
        });
        var campo = this.obterCampo(campoId);
        if (campo) campo.classList.add('ditado-ativo');
        this.mostrarBarraParar(true);
    };

    PanelDxVozDitado.prototype.mostrarBarraParar = function (visivel) {
        if (!this.stopBarEl) {
            this.stopBarEl = document.getElementById('ditado-stop-bar');
        }
        if (!this.stopBarEl) return;
        this.stopBarEl.hidden = !visivel;
        this.stopBarEl.setAttribute('aria-hidden', visivel ? 'false' : 'true');
    };

    PanelDxVozDitado.prototype.montarValorCampo = function (interim) {
        var base = (this.valorBase || '').trim();
        var sessao = (this.transcricaoSessao || '').trim();
        var pedaco = (sessao + (interim ? ((sessao ? ' ' : '') + interim.trim()) : '')).trim();
        if (!pedaco) return base;
        return base ? (base + ' ' + pedaco) : pedaco;
    };

    PanelDxVozDitado.prototype.atualizarCampoLive = function (interim, commitFinal) {
        if (!this.campoAlvo) return;
        this.campoAlvo.value = this.montarValorCampo(interim || '');
        this.campoAlvo.scrollTop = this.campoAlvo.scrollHeight;
        if (commitFinal) {
            this.campoAlvo.classList.add('ditado-recebeu');
            var self = this;
            window.setTimeout(function () {
                if (self.campoAlvo) self.campoAlvo.classList.remove('ditado-recebeu');
            }, 450);
            this.campoAlvo.dispatchEvent(new Event('input', { bubbles: true }));
        }
    };

    PanelDxVozDitado.prototype.limparTimers = function () {
        if (this._restartTimer) {
            window.clearTimeout(this._restartTimer);
            this._restartTimer = null;
        }
        if (this._startTimer) {
            window.clearTimeout(this._startTimer);
            this._startTimer = null;
        }
    };

    PanelDxVozDitado.prototype.finalizarSessao = function (silencioso) {
        this.limparTimers();
        this.sessionAtiva = false;
        this.paradaManual = false;
        this._reiniciosSessao = 0;
        this._iniciandoMotor = false;
        var campo = this.campoAlvo;
        this.campoAlvo = null;
        this.campoAlvoId = null;
        this.btnAtivo = null;
        this.valorBase = '';
        this.transcricaoSessao = '';
        this.mostrarBarraParar(false);
        this.resetarTodosMics();
        if (!silencioso) this.setStatus('');
        if (campo) campo.dispatchEvent(new Event('blur', { bubbles: true }));
    };

    PanelDxVozDitado.prototype.pararMotor = function () {
        if (!this.motor) return;
        var m = this.motor;
        this.motor = null;
        m.onstart = null;
        m.onresult = null;
        m.onerror = null;
        m.onend = null;
        m.onspeechstart = null;
        try { m.abort(); } catch (_) {}
        try { m.stop(); } catch (_) {}
    };

    PanelDxVozDitado.prototype.parar = function (silencioso, motivo) {
        this.paradaManual = true;
        this.sessionAtiva = false;
        this.limparTimers();
        this.pararMotor();
        var recebeu = this.recebeu;
        this.recebeu = false;
        this.finalizarSessao(silencioso);
        if (!silencioso) {
            if (motivo === 'palavra-chave') {
                this.setStatus('Ditado encerrado — palavra «fim» reconhecida. Texto salvo.');
            } else {
                this.setStatus(recebeu
                    ? 'Ditado encerrado — texto salvo.'
                    : 'Ditado encerrado.');
            }
        }
    };

    PanelDxVozDitado.prototype.pararPorPalavraChave = function (textoRestante) {
        if (textoRestante !== undefined) {
            this.transcricaoSessao = textoRestante;
            this.atualizarCampoLive('', true);
            this.recebeu = true;
        }
        this.parar(false, 'palavra-chave');
    };

    PanelDxVozDitado.prototype.ingestirTexto = function (texto, isFinal) {
        var parsed = this.processarParadaPorVoz(texto);
        if (parsed.stop) {
            var merged = this.transcricaoSessao
                ? (this.transcricaoSessao + (parsed.texto ? ' ' + parsed.texto : '')).trim()
                : parsed.texto;
            this.pararPorPalavraChave(merged);
            return true;
        }
        if (!parsed.texto) return false;
        if (isFinal) {
            this.transcricaoSessao = this.transcricaoSessao
                ? (this.transcricaoSessao + ' ' + parsed.texto)
                : parsed.texto;
            this.recebeu = true;
            this.atualizarCampoLive('', true);
            this.setStatus('Fale ou diga «fim» / clique em Parar ditado para encerrar.');
        } else {
            this.atualizarCampoLive(parsed.texto, false);
        }
        return false;
    };

    PanelDxVozDitado.prototype.criarMotor = function () {
        var SpeechRecognition = global.SpeechRecognition || global.webkitSpeechRecognition;
        if (!SpeechRecognition) return null;

        var self = this;
        var rec = new SpeechRecognition();
        rec.lang = 'pt-BR';
        rec.continuous = true;
        rec.interimResults = true;
        rec.maxAlternatives = 1;

        rec.onstart = function () {
            self._iniciandoMotor = false;
            self.marcarOuvindo(self.btnAtivo, self.campoAlvoId);
            self.setStatus('Gravando… Diga «fim» ou clique em Parar ditado quando terminar.');
        };

        rec.onspeechstart = function () {
            self.setStatus('Ouvindo você…');
        };

        rec.onresult = function (event) {
            if (!self.campoAlvo || !self.sessionAtiva) return;

            var interim = '';
            var finalDelta = '';

            for (var i = event.resultIndex; i < event.results.length; i++) {
                var chunk = (event.results[i][0] && event.results[i][0].transcript) || '';
                if (!chunk) continue;
                if (event.results[i].isFinal) {
                    finalDelta += chunk;
                } else {
                    interim += chunk;
                }
            }

            if (interim.trim() && self.ingestirTexto(interim.trim(), false)) return;

            if (finalDelta.trim()) {
                self.ingestirTexto(finalDelta.trim(), true);
            }
        };

        rec.onerror = function (event) {
            var err = event && event.error ? event.error : 'desconhecido';
            self._iniciandoMotor = false;

            if (err === 'not-allowed' || err === 'service-not-allowed') {
                self.notifyError('Permita o microfone no navegador e clique em Ditado novamente.', true);
                self.parar(true);
                return;
            }

            if (err === 'aborted') return;

            if (self.sessionAtiva && !self.paradaManual) {
                if (err === 'no-speech') {
                    self.setStatus('Silêncio detectado — continue falando ou diga «fim».');
                } else {
                    self.setStatus('Reconectando microfone…');
                }
                self.agendarReinicio(350, true);
            }
        };

        rec.onend = function () {
            self.motor = null;
            self._iniciandoMotor = false;
            if (self.sessionAtiva && !self.paradaManual) {
                self.agendarReinicio(200, true);
                return;
            }
            if (self.recebeu && !self.sessionAtiva) {
                self.setStatus('Texto salvo. Clique em Ditado para gravar outro trecho.');
            }
        };

        return rec;
    };

    PanelDxVozDitado.prototype.iniciarMotorNovo = function () {
        var self = this;
        if (!this.sessionAtiva || this.paradaManual || !this.campoAlvo) return;
        if (this._iniciandoMotor) return;

        this.pararMotor();
        this._iniciandoMotor = true;

        this._startTimer = window.setTimeout(function () {
            if (!self.sessionAtiva || self.paradaManual) {
                self._iniciandoMotor = false;
                return;
            }
            self.motor = self.criarMotor();
            if (!self.motor) {
                self._iniciandoMotor = false;
                self.notifyError('Ditado indisponível neste navegador. Use Chrome ou Edge.', true);
                self.parar(true);
                return;
            }
            try {
                self.motor.start();
            } catch (e) {
                self._iniciandoMotor = false;
                self.agendarReinicio(400, true);
            }
        }, 280);
    };

    PanelDxVozDitado.prototype.agendarReinicio = function (delay, forcarNovoMotor) {
        var self = this;
        this.limparTimers();

        if (this._reiniciosSessao >= MAX_REINICIOS_SESSAO) {
            this.setStatus('Pausa técnica — clique em Ditado para continuar neste campo.');
            this.parar(false);
            return;
        }

        this._restartTimer = window.setTimeout(function () {
            if (!self.sessionAtiva || self.paradaManual || !self.campoAlvo) return;
            self._reiniciosSessao += 1;
            if (forcarNovoMotor || !self.motor) {
                self.iniciarMotorNovo();
            } else {
                try {
                    self.motor.start();
                } catch (e) {
                    self.iniciarMotorNovo();
                }
            }
        }, delay || 200);
    };

    PanelDxVozDitado.prototype.alternar = function (campoId, btn) {
        if (!btn) {
            btn = this.root.querySelector('.btn-voz-campo[data-voz-target="' + campoId + '"]');
        }
        if (!btn) return;

        if (this.sessionAtiva && this.campoAlvoId === campoId) {
            this.parar(false);
            return;
        }

        var campo = this.obterCampo(campoId);
        if (!campo || campo.disabled || campo.readOnly) {
            this.notifyError('Este campo está bloqueado para edição.', true);
            return;
        }

        if (this.sessionAtiva) this.parar(true);

        this.campoAlvo = campo;
        this.campoAlvoId = campoId;
        this.btnAtivo = btn;
        this.valorBase = campo.value || '';
        this.transcricaoSessao = '';
        this.recebeu = false;
        this.paradaManual = false;
        this.sessionAtiva = true;
        this._reiniciosSessao = 0;

        this.setStatus('Abrindo microfone…');
        this.iniciarMotorNovo();
    };

    PanelDxVozDitado.prototype.init = function (options) {
        options = options || {};
        if (options.root) {
            this.root = typeof options.root === 'string'
                ? document.querySelector(options.root) : options.root;
        }
        if (!this.root) return this;

        if (options.statusEl) {
            this.statusEl = typeof options.statusEl === 'string'
                ? document.querySelector(options.statusEl) : options.statusEl;
        }
        this.stopBarEl = options.stopBarEl
            ? (typeof options.stopBarEl === 'string'
                ? document.querySelector(options.stopBarEl) : options.stopBarEl)
            : document.getElementById('ditado-stop-bar');

        if (options.onError) this.onError = options.onError;

        var self = this;
        if (this._boundClick) {
            this.root.removeEventListener('click', this._boundClick);
        }
        this._boundClick = function (e) {
            var stopBtn = e.target.closest('[data-ditado-action="stop"]');
            if (stopBtn) {
                e.preventDefault();
                if (self.sessionAtiva) self.parar(false);
                return;
            }
            var btn = e.target.closest('.btn-voz-campo');
            if (!btn || !self.root.contains(btn)) return;
            e.preventDefault();
            var campoId = btn.getAttribute('data-voz-target');
            if (campoId) self.alternar(campoId, btn);
        };
        this.root.addEventListener('click', this._boundClick);

        global.pararDitadoPanelDx = function () {
            if (self.sessionAtiva) self.parar(false);
        };

        return this;
    };

    PanelDxVozDitado.prototype.destroy = function () {
        this.parar(true);
        if (this._boundClick && this.root) {
            this.root.removeEventListener('click', this._boundClick);
        }
    };

    global.PanelDxVozDitado = PanelDxVozDitado;
    global.panelDxVozInstances = global.panelDxVozInstances || {};

    global.initPanelDxVozDitado = function (key, options) {
        var inst = new PanelDxVozDitado();
        inst.init(options);
        if (key) global.panelDxVozInstances[key] = inst;
        return inst;
    };
}(window));
