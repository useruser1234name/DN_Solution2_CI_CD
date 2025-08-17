# Generated manually for sensitive data handling

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='is_sensitive_data_processed',
            field=models.BooleanField(default=False, help_text='본사 승인 후 민감정보가 DB에 저장되었는지 여부', verbose_name='민감정보 처리 완료'),
        ),
        migrations.AddField(
            model_name='order',
            name='sensitive_data_key',
            field=models.CharField(blank=True, help_text='Redis에 저장된 민감정보의 키', max_length=255, null=True, verbose_name='민감정보 키'),
        ),
        migrations.CreateModel(
            name='OrderSensitiveData',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('customer_name_hash', models.CharField(max_length=64, verbose_name='고객명 해시')),
                ('customer_phone_hash', models.CharField(max_length=64, verbose_name='전화번호 해시')),
                ('customer_email_hash', models.CharField(blank=True, max_length=64, verbose_name='이메일 해시')),
                ('customer_address_hash', models.CharField(max_length=64, verbose_name='주소 해시')),
                ('customer_name_masked', models.CharField(max_length=100, verbose_name='고객명 (마스킹)')),
                ('customer_phone_masked', models.CharField(max_length=20, verbose_name='전화번호 (마스킹)')),
                ('customer_address_masked', models.TextField(verbose_name='주소 (마스킹)')),
                ('processed_at', models.DateTimeField(auto_now_add=True, verbose_name='처리일시')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='sensitive_data', to='orders.order', verbose_name='주문')),
            ],
            options={
                'verbose_name': '주문 민감정보',
                'verbose_name_plural': '주문 민감정보',
                'indexes': [
                    models.Index(fields=['order'], name='orders_orde_order_i_1f3b2e_idx'),
                    models.Index(fields=['processed_at'], name='orders_orde_process_8a7e1c_idx'),
                ],
            },
        ),
    ]