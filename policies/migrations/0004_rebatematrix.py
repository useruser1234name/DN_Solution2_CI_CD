# Generated manually for RebateMatrix model

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('policies', '0003_policyexposure_orderformtemplate_orderformfield_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='RebateMatrix',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='리베이트 매트릭스의 고유 식별자', primary_key=True, serialize=False)),
                ('carrier', models.CharField(choices=[('skt', 'SKT'), ('kt', 'KT'), ('lg', 'LG U+'), ('all', '전체')], help_text='리베이트가 적용될 통신사', max_length=10, verbose_name='통신사')),
                ('plan_range', models.IntegerField(choices=[(30000, '3만원대'), (50000, '5만원대'), (70000, '7만원대'), (100000, '10만원대'), (150000, '15만원대')], help_text='리베이트가 적용될 요금제 범위', verbose_name='요금제 범위')),
                ('contract_period', models.IntegerField(choices=[(3, '3개월'), (6, '6개월'), (9, '9개월'), (12, '12개월'), (24, '24개월'), (36, '36개월')], help_text='리베이트가 적용될 가입기간 (개월)', verbose_name='가입기간')),
                ('rebate_amount', models.DecimalField(decimal_places=2, help_text='해당 조건의 리베이트 금액', max_digits=10, verbose_name='리베이트 금액')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일시')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일시')),
                ('policy', models.ForeignKey(help_text='리베이트 매트릭스가 속한 정책', on_delete=django.db.models.deletion.CASCADE, related_name='rebate_matrix', to='policies.policy', verbose_name='정책')),
            ],
            options={
                'verbose_name': '리베이트 매트릭스',
                'verbose_name_plural': '리베이트 매트릭스',
                'ordering': ['policy', 'carrier', 'plan_range', 'contract_period'],
                'unique_together': {('policy', 'carrier', 'plan_range', 'contract_period')},
                'indexes': [
                    models.Index(fields=['policy', 'carrier'], name='policies_re_policy__b7c4f6_idx'),
                    models.Index(fields=['plan_range', 'contract_period'], name='policies_re_plan_ra_d6e3f8_idx'),
                ],
            },
        ),
    ]