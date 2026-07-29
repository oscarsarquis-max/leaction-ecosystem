'use client'

type Props = {
  packageUrl: string
  kind: 'SCORM' | 'H5P'
  title: string
}

/** Iframe sandbox para pacotes SCORM/H5P (xAPI via backend proxy). */
export default function ScormH5pFrame({ packageUrl, kind, title }: Props) {
  return (
    <div className="min-h-[480px] w-full" data-testid="scorm-root" data-kind={kind}>
      <iframe
        data-testid="scorm-iframe"
        title={title}
        src={packageUrl}
        sandbox="allow-scripts allow-same-origin allow-forms"
        className="h-[480px] w-full border-0"
        referrerPolicy="strict-origin-when-cross-origin"
      />
    </div>
  )
}
