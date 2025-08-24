# Generated for Commission Fact Table (Data Warehouse)

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('settlements', '0005_commission_grade_system'),
        ('companies', '0001_initial'),
        ('policies', '0012_rename_rebatematrix_commissionmatrix_and_more'),
        ('orders', '0008_final_status_and_history'),
    ]

    operations = [
        migrations.CreateModel(
            name='CommissionFact',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date_key', models.DateField(verbose_name='날짜 차원')),
                ('carrier', models.CharField(help_text='SKT, KT, LG, all', max_length=10, verbose_name='통신사')),
                ('plan_range', models.IntegerField(help_text='요금제 금액대 (11000, 22000, ...165000)', verbose_name='요금제 범위')),
                ('contract_period', models.IntegerField(help_text='계약기간 (12, 24, 36, 48개월)', verbose_name='계약기간')),
                ('base_commission', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='기본 수수료')),
                ('grade_bonus', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='그레이드 보너스')),
                ('total_commission', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='총 수수료')),
                ('settlement_status', models.CharField(help_text='pending, approved, paid, unpaid, cancelled', max_length=20, verbose_name='정산 상태')),
                ('payment_status', models.CharField(help_text='pending, paid, unpaid', max_length=20, verbose_name='입금 상태')),
                ('order_count_in_period', models.IntegerField(default=1, help_text='해당 기간 내 업체의 누적 주문 수', verbose_name='기간 내 주문 수')),
                ('achieved_grade_level', models.IntegerField(default=0, verbose_name='달성 그레이드 레벨')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일시')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일시')),
                ('batch_id', models.CharField(blank=True, help_text='ETL 배치 처리 시 사용되는 배치 식별자', max_length=100, verbose_name='배치 ID')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='commission_facts', to='companies.company', verbose_name='업체')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='commission_facts', to='orders.order', verbose_name='주문')),
                ('policy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='commission_facts', to='policies.policy', verbose_name='정책')),
            ],
            options={
                'verbose_name': '수수료 팩트',
                'verbose_name_plural': '수수료 팩트 테이블',
                'ordering': ['-date_key', '-created_at'],
                'indexes': [
                    models.Index(fields=['date_key', 'company'], name='settlements_commissionfact_date_company_idx'),
                    models.Index(fields=['date_key', 'policy'], name='settlements_commissionfact_date_policy_idx'),
                    models.Index(fields=['company', 'settlement_status'], name='settlements_commissionfact_company_status_idx'),
                    models.Index(fields=['policy', 'date_key'], name='settlements_commissionfact_policy_date_idx'),
                    models.Index(fields=['carrier', 'plan_range'], name='settlements_commissionfact_carrier_plan_idx'),
                    models.Index(fields=['achieved_grade_level'], name='settlements_commissionfact_grade_level_idx'),
                    models.Index(fields=['batch_id'], name='settlements_commissionfact_batch_id_idx'),
                ],
            },
        ),
        migrations.AlterUniqueTogether(
            name='commissionfact',
            unique_together={('order', 'company')},
        ),
    ]
