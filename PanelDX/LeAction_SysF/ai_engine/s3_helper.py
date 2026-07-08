import boto3
import traceback


def upload_to_s3(file_path, id_matu, id_surv): # <-- Adicione id_surv aqui
    """
    Envia o PDF gerado pelo Worker para o bucket de diagnósticos.
    Gera uma URL assinada válida por 7 dias.
    """
    s3_client = boto3.client('s3', region_name='us-east-2')

    # Nomeamos o arquivo com MATU e SURV para garantir a imutabilidade/histórico
    bucket_name = 'diagnostico-reports-diagnosis-2025'
    s3_key = f"diagnosticos/IA_Diagnostico_M{id_matu}_S{id_surv}.pdf"

    try:
        print(f"☁️ Enviando PDF para o S3 (Bucket: {bucket_name})...")

        # Faz o upload (o arquivo nasce PRIVADO no S3)
        s3_client.upload_file(
            file_path,
            bucket_name,
            s3_key,
            ExtraArgs={'ContentType': 'application/pdf'}
        )

        # GERA A URL ASSINADA (Agora com 604800 segundos = 7 dias)
        url_assinada = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': s3_key},
            ExpiresIn=604800
        )

        print(f"✅ Upload concluído. URL Assinada (7 dias) para M{id_matu}_S{id_surv}")
        return url_assinada

    except Exception as e:
        print(f"❌ Erro crítico no S3_Helper: {e}")
        import traceback
        traceback.print_exc()
        return None