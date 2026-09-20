package br.com.segsense.application.urlcapture;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface UrlCaptureRepository {

  void insertCapture(UrlCaptureRecord record);

  Optional<UrlCaptureRecord> findCapture(UUID id);

  void insertConfirmation(UrlCaptureConfirmationRecord record);

  Optional<UrlCaptureConfirmationRecord> findLatestConfirmation(UUID captureId);

  List<UrlCaptureConfirmationRecord> confirmationsOf(UUID captureId);
}
