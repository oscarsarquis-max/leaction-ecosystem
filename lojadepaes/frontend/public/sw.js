/* Notificação da Loja. Sem cache de página, pedido, pagamento ou sessão. */
self.addEventListener("push", function (event) {
  var data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (error) {
    data = {};
  }
  var title = typeof data.title === "string" ? data.title.slice(0, 120) : "Loja de Pães";
  var body = typeof data.body === "string" ? data.body.slice(0, 180) : "Abra o painel para ver.";
  var path = safeAdminPath(data.path);
  var tag = typeof data.tag === "string" ? data.tag.slice(0, 64) : "lojadepaes";
  event.waitUntil(
    self.registration.showNotification(title, {
      body: body,
      data: { path: path },
      tag: tag,
    }),
  );
});

self.addEventListener("notificationclick", function (event) {
  event.notification.close();
  var path = safeAdminPath(event.notification.data && event.notification.data.path);
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (list) {
      for (var i = 0; i < list.length; i += 1) {
        var client = list[i];
        if (new URL(client.url).origin !== self.location.origin) {
          continue;
        }
        if (client.navigate) {
          return client.focus().then(function () {
            return client.navigate(path);
          });
        }
      }
      return self.clients.openWindow(path);
    }),
  );
});

function safeAdminPath(raw) {
  if (typeof raw !== "string" || !raw.startsWith("/admin/pedidos")) {
    return "/admin/pedidos";
  }
  if (raw.startsWith("//") || raw.indexOf("\\") !== -1 || raw.indexOf("://") !== -1 || raw.indexOf("..") !== -1) {
    return "/admin/pedidos";
  }
  try {
    var url = new URL(raw, self.location.origin);
    if (url.origin !== self.location.origin) {
      return "/admin/pedidos";
    }
    if (url.pathname !== "/admin/pedidos" && url.pathname.indexOf("/admin/pedidos/") !== 0) {
      return "/admin/pedidos";
    }
    return url.pathname;
  } catch (error) {
    return "/admin/pedidos";
  }
}
