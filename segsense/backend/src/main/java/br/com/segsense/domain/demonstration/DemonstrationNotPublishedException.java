package br.com.segsense.domain.demonstration;

public class DemonstrationNotPublishedException extends RuntimeException {

  public DemonstrationNotPublishedException() {
    super("demonstration-not-published");
  }
}
