package br.com.banco.spider.canonical.versioning;

import java.util.Objects;

/**
 * Referência versionada e governada (não é URL livre).
 *
 * @param ref identificador lógico opaco
 * @param version versão publicada (ex.: 1.0.0); pode ser null quando a resolução fixa depois
 */
public record VersionedReference(String ref, String version) {

  public VersionedReference {
    Objects.requireNonNull(ref, "ref");
    ref = ref.trim();
    if (ref.isEmpty()) {
      throw new IllegalArgumentException("ref must not be blank");
    }
    if (version != null) {
      version = version.trim();
      if (version.isEmpty()) {
        version = null;
      }
    }
  }

  public static VersionedReference of(String ref) {
    return new VersionedReference(ref, null);
  }

  public static VersionedReference of(String ref, String version) {
    return new VersionedReference(ref, version);
  }
}
