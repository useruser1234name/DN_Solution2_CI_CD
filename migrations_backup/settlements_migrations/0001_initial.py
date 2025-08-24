# Generated manually for settlements app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('companies', '0001_initial'),
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Settlement',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='정산 ID')),
                ('rebate_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='리베이트 금액')),
                ('status', models.CharField(choices=[('pending', '정산 대기'), ('approved', '승인됨'), ('paid', '지급 완료'), ('cancelled', '취소됨')], default='pending', max_length=20, verbose_name='정산 상태')),
                ('approved_at', models.DateTimeField(blank=True, null=True, verbose_name='승인일시')),
                ('paid_at', models.DateTimeField(blank=True, null=True, verbose_name='지급일시')),
                ('notes', models.TextField(blank=True, verbose_name='메모')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일시')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일시')),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_settlements', to=settings.AUTH_USER_MODEL, verbose_name='승인자')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='settlements', to='companies.company', verbose_name='정산 대상 업체')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='settlements', to='orders.order', verbose_name='주문')),
            ],
            options={
                'verbose_name': '정산',
                'verbose_name_plural': '정산 목록',
                'ordering': ['-created_at'],
                'unique_together': {('order', 'company')},
                'indexes': [
                    models.Index(fields=['order', 'company'], name='settlements_order_i_abc123_idx'),
                    models.Index(fields=['company', 'status'], name='settlements_company_def456_idx'),
                    models.Index(fields=['status', 'created_at'], name='settlements_status_ghi789_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='SettlementBatch',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='배치 ID')),
                ('title', models.CharField(max_length=200, verbose_name='배치명')),
                ('description', models.TextField(blank=True, verbose_name='설명')),
                ('start_date', models.DateField(verbose_name='시작일')),
                ('end_date', models.DateField(verbose_name='종료일')),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='총 정산 금액')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일시')),
                ('approved_at', models.DateTimeField(blank=True, null=True, verbose_name='승인일시')),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_batches', to=settings.AUTH_USER_MODEL, verbose_name='승인자')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='생성자')),
            ],
            options={
                'verbose_name': '정산 배치',
                'verbose_name_plural': '정산 배치 목록',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['start_date', 'end_date'], name='settlements_batch_jkl012_idx'),
                    models.Index(fields=['created_at'], name='settlements_batch_mno345_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='SettlementBatchItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('added_at', models.DateTimeField(auto_now_add=True, verbose_name='추가일시')),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='settlements.settlementbatch', verbose_name='배치')),
                ('settlement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='batch_items', to='settlements.settlement', verbose_name='정산')),
            ],
            options={
                'verbose_name': '정산 배치 항목',
                'verbose_name_plural': '정산 배치 항목',
                'unique_together': {('batch', 'settlement')},
                'indexes': [
                    models.Index(fields=['batch', 'settlement'], name='settlements_item_pqr678_idx'),
                ],
            },
        ),
    ]