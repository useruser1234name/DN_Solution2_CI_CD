# Generated for Settlement status expansion (Phase 2-1)
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('settlements', '0003_add_rebate_due_date'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.AlterField(
            model_name='settlement',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', '정산 대기'),
                    ('approved', '정산 승인'),
                    ('paid', '입금 완료'),
                    ('unpaid', '미입금'),
                    ('cancelled', '취소됨'),
                ],
                default='pending',
                max_length=20,
                verbose_name='정산 상태'
            ),
        ),
        migrations.CreateModel(
            name='SettlementStatusHistory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('from_status', models.CharField(choices=[('pending', '정산 대기'), ('approved', '정산 승인'), ('paid', '입금 완료'), ('unpaid', '미입금'), ('cancelled', '취소됨')], max_length=20, verbose_name='이전 상태')),
                ('to_status', models.CharField(choices=[('pending', '정산 대기'), ('approved', '정산 승인'), ('paid', '입금 완료'), ('unpaid', '미입금'), ('cancelled', '취소됨')], max_length=20, verbose_name='변경 상태')),
                ('reason', models.TextField(blank=True, verbose_name='변경 사유')),
                ('changed_at', models.DateTimeField(auto_now_add=True, verbose_name='변경일시')),
                ('user_ip', models.GenericIPAddressField(blank=True, null=True, verbose_name='사용자 IP')),
                ('user_agent', models.TextField(blank=True, verbose_name='사용자 에이전트')),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user', verbose_name='변경자')),
                ('settlement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_history', to='settlements.settlement', verbose_name='정산')),
            ],
            options={
                'verbose_name': '정산 상태 이력',
                'verbose_name_plural': '정산 상태 이력',
                'ordering': ['-changed_at'],
            },
        ),
        migrations.AddIndex(
            model_name='settlementstatushistory',
            index=models.Index(fields=['settlement', 'changed_at'], name='settlements_settlement_history_idx'),
        ),
        migrations.AddIndex(
            model_name='settlementstatushistory',
            index=models.Index(fields=['to_status'], name='settlements_settlement_status_idx'),
        ),
        migrations.AddIndex(
            model_name='settlementstatushistory',
            index=models.Index(fields=['changed_by'], name='settlements_settlement_user_idx'),
        ),
    ]
