package br.com.banco.spider.execution.support;

import java.util.UUID;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Supplier;

public interface IdentifierGenerator {
  String nextId(String prefix);

  static IdentifierGenerator uuid() {
    return prefix -> prefix + "-" + UUID.randomUUID();
  }

  static IdentifierGenerator sequential(String prefixBase) {
    AtomicLong seq = new AtomicLong(0);
    return prefix -> prefix + "-" + prefixBase + "-" + seq.incrementAndGet();
  }

  static IdentifierGenerator fixed(Supplier<String> supplier) {
    return prefix -> prefix + "-" + supplier.get();
  }
}
