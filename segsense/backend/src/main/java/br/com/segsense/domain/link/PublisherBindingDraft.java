package br.com.segsense.domain.link;

import java.math.BigDecimal;

public record PublisherBindingDraft(String fieldKey, Object value) {

  public PublisherBindingDraft {
    if (fieldKey == null || fieldKey.isBlank()) {
      throw new InvalidPublisherContextException();
    }
    fieldKey = fieldKey.trim();
    if (value == null) {
      throw new InvalidPublisherContextException();
    }
  }

  public boolean isText() {
    return value instanceof String;
  }

  public boolean isNumber() {
    return value instanceof BigDecimal;
  }

  public boolean isBoolean() {
    return value instanceof Boolean;
  }

  public String text() {
    if (!(value instanceof String text)) {
      throw new InvalidPublisherContextException();
    }
    return text;
  }

  public BigDecimal number() {
    if (!(value instanceof BigDecimal number)) {
      throw new InvalidPublisherContextException();
    }
    return number;
  }

  public Boolean bool() {
    if (!(value instanceof Boolean flag)) {
      throw new InvalidPublisherContextException();
    }
    return flag;
  }
}
