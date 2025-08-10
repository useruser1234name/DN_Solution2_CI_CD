"""
성능 최적화를 위한 데이터베이스 인덱스 추가
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    
    dependencies = [
        ('companies', '0001_initial'),
        ('policies', '0001_initial'),
        ('orders', '0001_initial'),
    ]
    
    operations = [
        # Company 인덱스
        migrations.AddIndex(
            model_name='company',
            index=models.Index(
                fields=['type', 'status', '-created_at'],
                name='company_type_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='company',
            index=models.Index(
                fields=['parent_company', 'status'],
                name='company_parent_status_idx'
            ),
        ),
        
        # CompanyUser 인덱스
        migrations.AddIndex(
            model_name='companyuser',
            index=models.Index(
                fields=['company', 'status', 'is_approved'],
                name='compuser_comp_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='companyuser',
            index=models.Index(
                fields=['username', 'status'],
                name='compuser_username_idx'
            ),
        ),
        
        # Policy 인덱스
        migrations.AddIndex(
            model_name='policy',
            index=models.Index(
                fields=['expose', 'premium_market_expose', '-created_at'],
                name='policy_expose_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='policy',
            index=models.Index(
                fields=['form_type', 'carrier', 'contract_period'],
                name='policy_filter_idx'
            ),
        ),
        
        # PolicyAssignment 인덱스
        migrations.AddIndex(
            model_name='policyassignment',
            index=models.Index(
                fields=['company', 'policy', 'expose_to_child'],
                name='policy_assign_comp_idx'
            ),
        ),
        
        # Order 인덱스
        migrations.AddIndex(
            model_name='order',
            index=models.Index(
                fields=['company', 'status', '-created_at'],
                name='order_comp_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(
                fields=['customer_phone', 'status'],
                name='order_customer_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(
                fields=['policy', 'status', '-created_at'],
                name='order_policy_idx'
            ),
        ),
        
        # Invoice 인덱스
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(
                fields=['courier', 'invoice_number'],
                name='invoice_tracking_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(
                fields=['delivered_at', '-sent_at'],
                name='invoice_delivery_idx'
            ),
        ),
    ]
