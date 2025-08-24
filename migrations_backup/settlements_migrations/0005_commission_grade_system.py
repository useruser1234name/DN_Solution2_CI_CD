# Generated for Commission Grade System

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('settlements', '0005_settlement_payment_fields'),
        ('policies', '0012_rename_rebatematrix_commissionmatrix_and_more'),  # 정책 앱의 최신 마이그레이션
    ]

    operations = [
        migrations.CreateModel(
            name='CommissionGradeTracking',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('period_type', models.CharField(choices=[('monthly', '월별'), ('quarterly', '분기별'), ('yearly', '연별'), ('lifetime', '누적')], max_length=20, verbose_name='기간 타입')),
                ('period_start', models.DateField(verbose_name='기간 시작일')),
                ('period_end', models.DateField(verbose_name='기간 종료일')),
                ('current_orders', models.IntegerField(default=0, verbose_name='현재 주문 수')),
                ('target_orders', models.IntegerField(verbose_name='목표 주문 수')),
                ('achieved_grade_level', models.IntegerField(default=0, verbose_name='달성 그레이드 레벨')),
                ('bonus_per_order', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='주문당 보너스 수수료')),
                ('total_bonus', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='총 보너스 금액')),
                ('is_active', models.BooleanField(default=True, verbose_name='활성화 여부')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일시')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일시')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='grade_tracking', to='companies.company', verbose_name='업체')),
                ('policy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='grade_tracking', to='policies.policy', verbose_name='정책')),
            ],
            options={
                'verbose_name': '수수료 그레이드 추적',
                'verbose_name_plural': '수수료 그레이드 추적',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['company', 'period_type'], name='settlements_commissiongradetracking_company_period_idx'),
                    models.Index(fields=['policy', 'period_start', 'period_end'], name='settlements_commissiongradetracking_policy_period_idx'),
                    models.Index(fields=['achieved_grade_level'], name='settlements_commissiongradetracking_grade_level_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='GradeAchievementHistory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('from_level', models.IntegerField(verbose_name='이전 레벨')),
                ('to_level', models.IntegerField(verbose_name='변경 레벨')),
                ('orders_at_change', models.IntegerField(verbose_name='변경시 주문 수')),
                ('bonus_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='보너스 금액')),
                ('achieved_at', models.DateTimeField(auto_now_add=True, verbose_name='달성일시')),
                ('grade_tracking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='achievement_history', to='settlements.commissiongradetracking', verbose_name='그레이드 추적')),
            ],
            options={
                'verbose_name': '그레이드 달성 이력',
                'verbose_name_plural': '그레이드 달성 이력',
                'ordering': ['-achieved_at'],
                'indexes': [
                    models.Index(fields=['grade_tracking', 'achieved_at'], name='settlements_gradeachievementhistory_tracking_achieved_idx'),
                    models.Index(fields=['to_level'], name='settlements_gradeachievementhistory_to_level_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='GradeBonusSettlement',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('bonus_amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='보너스 금액')),
                ('status', models.CharField(choices=[('pending', '정산 대기'), ('approved', '정산 승인'), ('paid', '지급 완료'), ('cancelled', '취소됨')], default='pending', max_length=20, verbose_name='정산 상태')),
                ('approved_at', models.DateTimeField(blank=True, null=True, verbose_name='승인일시')),
                ('paid_at', models.DateTimeField(blank=True, null=True, verbose_name='지급일시')),
                ('notes', models.TextField(blank=True, verbose_name='메모')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일시')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일시')),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_bonus_settlements', to='auth.user', verbose_name='승인자')),
                ('grade_tracking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bonus_settlements', to='settlements.commissiongradetracking', verbose_name='그레이드 추적')),
            ],
            options={
                'verbose_name': '그레이드 보너스 정산',
                'verbose_name_plural': '그레이드 보너스 정산',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['grade_tracking', 'status'], name='settlements_gradebonussettlement_tracking_status_idx'),
                    models.Index(fields=['status', 'created_at'], name='settlements_gradebonussettlement_status_created_idx'),
                ],
            },
        ),
        migrations.AlterUniqueTogether(
            name='commissiongradetracking',
            unique_together={('company', 'policy', 'period_type', 'period_start')},
        ),
    ]
