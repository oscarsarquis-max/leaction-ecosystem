let suspendedFile: File | null = null;

export function suspendStatementFile(file: File | null) {
  suspendedFile = file;
}

export function peekStatementFile(): File | null {
  return suspendedFile;
}

export function clearStatementFile() {
  suspendedFile = null;
}
