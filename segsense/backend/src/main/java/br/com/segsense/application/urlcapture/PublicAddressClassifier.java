package br.com.segsense.application.urlcapture;

import java.net.Inet4Address;
import java.net.Inet6Address;
import java.net.InetAddress;
import java.util.Locale;

/** Classifies resolved addresses. Blocks loopback, private, link-local, multicast, metadata. */
public final class PublicAddressClassifier {

  private PublicAddressClassifier() {}

  public static boolean isBlockedHostname(String host) {
    if (host == null || host.isBlank()) {
      return true;
    }
    String normalized = host.toLowerCase(Locale.ROOT).replaceAll("\\.$", "");
    return normalized.equals("localhost")
        || normalized.equals("metadata.google.internal")
        || normalized.equals("metadata.google.com")
        || normalized.equals("metadata")
        || normalized.endsWith(".localhost")
        || normalized.endsWith(".internal")
        || normalized.endsWith(".local");
  }

  public static boolean isBlocked(InetAddress address) {
    if (address == null) {
      return true;
    }
    InetAddress unwrapped = unwrapMapped(address);
    if (unwrapped.isAnyLocalAddress()
        || unwrapped.isLoopbackAddress()
        || unwrapped.isLinkLocalAddress()
        || unwrapped.isSiteLocalAddress()
        || unwrapped.isMulticastAddress()) {
      return true;
    }
    byte[] raw = unwrapped.getAddress();
    if (unwrapped instanceof Inet4Address) {
      return isBlockedIpv4(raw);
    }
    if (unwrapped instanceof Inet6Address ipv6) {
      return isBlockedIpv6(ipv6);
    }
    return true;
  }

  static InetAddress unwrapMapped(InetAddress address) {
    if (address instanceof Inet6Address ipv6 && ipv6.isIPv4CompatibleAddress()) {
      byte[] raw = ipv6.getAddress();
      try {
        return InetAddress.getByAddress(new byte[] {raw[12], raw[13], raw[14], raw[15]});
      } catch (Exception ignored) {
        return address;
      }
    }
    if (address instanceof Inet6Address ipv6) {
      byte[] raw = ipv6.getAddress();
      boolean mapped = true;
      for (int i = 0; i < 10; i++) {
        if (raw[i] != 0) {
          mapped = false;
          break;
        }
      }
      if (mapped && raw[10] == (byte) 0xff && raw[11] == (byte) 0xff) {
        try {
          return InetAddress.getByAddress(new byte[] {raw[12], raw[13], raw[14], raw[15]});
        } catch (Exception ignored) {
          return address;
        }
      }
    }
    return address;
  }

  private static boolean isBlockedIpv4(byte[] raw) {
    int a = raw[0] & 0xff;
    int b = raw[1] & 0xff;
    int c = raw[2] & 0xff;
    int d = raw[3] & 0xff;
    if (a == 0 || a == 10 || a == 127) {
      return true;
    }
    if (a == 100 && b >= 64 && b <= 127) {
      return true;
    }
    if (a == 169 && b == 254) {
      return true;
    }
    if (a == 172 && b >= 16 && b <= 31) {
      return true;
    }
    if (a == 192 && b == 168) {
      return true;
    }
    if (a == 192 && b == 0 && (c == 0 || c == 2)) {
      return true;
    }
    if (a == 198 && (b == 18 || b == 51) ) {
      return true;
    }
    if (a == 198 && b == 51 && c == 100) {
      return true;
    }
    if (a == 203 && b == 0 && c == 113) {
      return true;
    }
    if (a >= 224) {
      return true;
    }
    if (a == 255 && b == 255 && c == 255 && d == 255) {
      return true;
    }
    return false;
  }

  private static boolean isBlockedIpv6(Inet6Address address) {
    byte[] raw = address.getAddress();
    if (raw[0] == (byte) 0xfc || raw[0] == (byte) 0xfd) {
      return true;
    }
    if (raw[0] == (byte) 0xfe && (raw[1] & 0xc0) == 0x80) {
      return true;
    }
    if (raw[0] == (byte) 0xff) {
      return true;
    }
    boolean allZero = true;
    for (byte value : raw) {
      if (value != 0) {
        allZero = false;
        break;
      }
    }
    return allZero;
  }
}
