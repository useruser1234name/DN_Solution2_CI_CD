# Generated for OrderHistory model
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0006_telecomorder_orderstatushistory'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', '접수대기'),
                    ('approved', '승인됨'),
                    ('processing', '개통 준비중'),
                    ('shipped', '개통중'),
                    ('completed', '개통완료'),
                    ('final_approved', '승인(완료)'),
                    ('cancelled', '개통취소'),
                ],
                default='pending',
                max_length=20,
                verbose_name='주문 상태'
            ),
        ),
        migrations.CreateModel(
            name='OrderHistory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('from_status', models.CharField(choices=[('pending', '접수대기'), ('approved', '승인됨'), ('processing', '개통 준비중'), ('shipped', '개통중'), ('completed', '개통완료'), ('final_approved', '승인(완료)'), ('cancelled', '개통취소')], max_length=20, verbose_name='이전 상태')),
                ('to_status', models.CharField(choices=[('pending', '접수대기'), ('approved', '승인됨'), ('processing', '개통 준비중'), ('shipped', '개통중'), ('completed', '개통완료'), ('final_approved', '승인(완료)'), ('cancelled', '개통취소')], max_length=20, verbose_name='변경 상태')),
                ('reason', models.TextField(blank=True, verbose_name='변경 사유')),
                ('changed_at', models.DateTimeField(auto_now_add=True, verbose_name='변경일시')),
                ('user_ip', models.GenericIPAddressField(blank=True, null=True, verbose_name='사용자 IP')),
                ('user_agent', models.TextField(blank=True, verbose_name='사용자 에이전트')),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user', verbose_name='변경자')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='history', to='orders.order', verbose_name='주문')),
            ],
            options={
                'verbose_name': '주문 상태 이력',
                'verbose_name_plural': '주문 상태 이력',
                'ordering': ['-changed_at'],
            },
        ),
        migrations.AddIndex(
            model_name='orderhistory',
            index=models.Index(fields=['order', 'changed_at'], name='orders_orde_order_h_idx'),
        ),
        migrations.AddIndex(
            model_name='orderhistory',
            index=models.Index(fields=['to_status'], name='orders_orde_to_stat_h_idx'),
        ),
        migrations.AddIndex(
            model_name='orderhistory',
            index=models.Index(fields=['changed_by'], name='orders_orde_changed_h_idx'),
        ),
    ]
