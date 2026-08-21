package br.com.banco.spider.execution.signal;

public interface InboxDeduplicationKeyPort {
  String deduplicationKeyHash(String sourceRef, String messageId);
}
