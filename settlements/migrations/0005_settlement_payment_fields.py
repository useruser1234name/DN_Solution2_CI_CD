# Generated for Settlement payment fields (Phase 2-3)
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settlements', '0004_settlement_status_expansion'),
    ]

    operations = [
        migrations.AddField(
            model_name='settlement',
            name='payment_method',
            field=models.CharField(
                blank=True,
                help_text='계좌이체, 현금, 카드 등',
                max_length=50,
                verbose_name='입금 방법'
            ),
        ),
        migrations.AddField(
            model_name='settlement',
            name='payment_reference',
            field=models.CharField(
                blank=True,
                help_text='거래번호, 승인번호 등',
                max_length=100,
                verbose_name='입금 참조번호'
            ),
        ),
        migrations.AddField(
            model_name='settlement',
            name='expected_payment_date',
            field=models.DateField(
                blank=True,
                help_text='입금이 예상되는 날짜',
                null=True,
                verbose_name='입금 예정일'
            ),
        ),
        # 인덱스 추가
        migrations.AddIndex(
            model_name='settlement',
            index=models.Index(
                fields=['expected_payment_date'],
                name='settlements_expected_payment_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='settlement',
            index=models.Index(
                fields=['payment_method'],
                name='settlements_payment_method_idx'
            ),
        ),
    ]
