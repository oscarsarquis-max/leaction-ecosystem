import segsenseLogoHeader from '../../images/segsense-logo-header.png';

type SegSenseLogoProps = {
  surface: 'admin' | 'public';
  withName?: boolean;
};

export default function SegSenseLogo(props: SegSenseLogoProps) {
  const redundantName = props.withName === true;
  return (
    <span className={`brand brand--${props.surface}`}>
      <img
        className={`brand-logo brand-logo--${props.surface}`}
        src={segsenseLogoHeader}
        alt={redundantName ? '' : 'SegSense'}
        width={props.surface === 'admin' ? 106 : 160}
        height={props.surface === 'admin' ? 60 : 90}
      />
      {redundantName ? <span className="brand-name">SegSense</span> : null}
    </span>
  );
}
