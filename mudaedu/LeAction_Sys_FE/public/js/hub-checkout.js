(function () {

  function resolveHubApi(raw) {
    var value = (raw || '').trim();
    if (!value || value.charAt(0) === '/') {
      return (value || '/hub-api').replace(/\/$/, '');
    }
    // URLs absolutas legadas (ex.: IP fixo na LAN) → proxy same-origin
    return '/hub-api';
  }

  function resolveHubPublicUrl(cfg) {
    if (cfg.hubPublicUrl && cfg.hubPublicUrl.indexOf('://') > 0) {
      return cfg.hubPublicUrl.replace(/\/$/, '');
    }
    var host = window.location.hostname;
    var protocol = window.location.protocol;
    var port = cfg.hubPort || '4000';
    return protocol + '//' + host + ':' + port;
  }

  function readConfig() {

    const el = document.getElementById('hub-checkout-config');

    if (!el) return null;

    return {

      hubApi: resolveHubApi(el.getAttribute('data-hub-api')),

      hubPublicUrl: (el.getAttribute('data-hub-public-url') || '').replace(/\/$/, ''),

      hubPort: el.getAttribute('data-hub-port') || '4000',

      webhookUrl: el.getAttribute('data-webhook-url') || '',

      idMatu: el.getAttribute('data-id-matu') || '',

      customerEmail: el.getAttribute('data-customer-email') || '',

      customerName: el.getAttribute('data-customer-name') || 'LeActioner',

      sku: el.getAttribute('data-sku') || 'PANEL_MATURIDADE',

      amount: Number(el.getAttribute('data-amount') || '850'),

      clientId: el.getAttribute('data-client-id') || 'MudaEdu',

    };

  }



  function buildCheckoutRedirect(cfg, paymentId, apiCheckoutUrl) {

    const orderId = String(paymentId || '').trim();

    if (!orderId) {

      throw new Error('Action Hub nao retornou payment_id (UUID do pedido).');

    }



    var hubOrigin = resolveHubPublicUrl(cfg);

    if (apiCheckoutUrl) {
      try {
        return apiCheckoutUrl;
      } catch (e) {
        /* fallback abaixo */
      }
    }

    var params = new URLSearchParams();

    params.set('checkout', orderId);

    params.set('email', cfg.customerEmail);

    var returnPath = window.location.pathname || '/projeto';

    if (window.location.search) {

      returnPath += window.location.search;

    }

    params.set('return_to', returnPath);

    params.set('return_origin', window.location.origin);

    params.set('client', cfg.clientId || 'MudaEdu');

    return hubOrigin + '/dashboard?' + params.toString();

  }



  async function iniciarCheckoutHub(btn) {

    const cfg = readConfig();

    if (!cfg) {

      alert('Configuracao do Action Hub nao encontrada.');

      return;

    }



    if (!cfg.idMatu) {

      alert('ID de maturidade nao disponivel para contratacao.');

      return;

    }



    if (!cfg.customerEmail || !cfg.customerEmail.includes('@')) {

      alert('E-mail do cliente nao disponivel. Faca login novamente.');

      return;

    }



    if (!cfg.webhookUrl) {

      alert('URL de webhook do MudaEdu nao configurada.');

      return;

    }



    const labelOriginal = btn.innerHTML;

    btn.disabled = true;

    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';



    var returnPath = window.location.pathname || '/projeto';

    if (window.location.search) {

      returnPath += window.location.search;

    }



    try {

      const res = await fetch(cfg.hubApi + '/v1/payments', {

        method: 'POST',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify({

          client_id: cfg.clientId,

          sku: cfg.sku,

          amount: cfg.amount,

          id_matu: String(cfg.idMatu),

          customer: {

            email: cfg.customerEmail,

            name: cfg.customerName,

          },

          webhook_url: cfg.webhookUrl,

          hub_public_url: resolveHubPublicUrl(cfg),

          return_to: returnPath,

          return_origin: window.location.origin,

        }),

      });



      const data = await res.json().catch(function () {

        return {};

      });



      if (!res.ok) {

        const msg =

          data.error ||

          (Array.isArray(data.missing) ? 'Campos ausentes: ' + data.missing.join(', ') : null) ||

          'Falha ao iniciar pagamento no Action Hub.';

        throw new Error(msg);

      }



      const checkoutUrl = buildCheckoutRedirect(cfg, data.payment_id, data.checkout_url);

      console.info('[Hub Checkout] payment_id:', data.payment_id);

      console.info('[Hub Checkout] checkout_url API:', data.checkout_url || '(ausente)');

      console.info('[Hub Checkout] redirect final:', checkoutUrl);



      window.location.assign(checkoutUrl);

    } catch (err) {

      console.error('[Hub Checkout]', err);

      alert(err.message || 'Nao foi possivel iniciar a contratacao.');

      btn.disabled = false;

      btn.innerHTML = labelOriginal;

    }

  }



  document.addEventListener('DOMContentLoaded', function () {

    document.querySelectorAll('[data-hub-checkout]').forEach(function (btn) {

      btn.addEventListener('click', function (e) {

        e.preventDefault();

        iniciarCheckoutHub(btn);

      });

    });

  });

})();
