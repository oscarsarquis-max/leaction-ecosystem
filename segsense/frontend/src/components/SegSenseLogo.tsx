import segsenseLogo from '../../images/segsense logo.png';

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
        src={segsenseLogo}
        alt={redundantName ? '' : 'SegSense'}
        width={props.surface === 'admin' ? 72 : 160}
        height={props.surface === 'admin' ? 72 : 160}
      />
      {redundantName ? <span className="brand-name">SegSense</span> : null}
    </span>
  );
}
