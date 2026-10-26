from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('shoping_app', '0003_productimage')]
    operations = [
        migrations.AddField('product', 'sale_price', models.DecimalField(blank=True, decimal_places=2, max_digits=9, null=True)),
        migrations.AddField('product', 'sizes', models.JSONField(blank=True, default=list)),
        migrations.AddField('product', 'size_stock', models.JSONField(blank=True, default=dict)),
        migrations.AddField('orderitem', 'unit_cost', models.DecimalField(decimal_places=2, default=0, max_digits=9)),
        migrations.CreateModel(name='BusinessExpense', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('name', models.CharField(max_length=140)), ('category', models.CharField(max_length=80)),
            ('amount', models.DecimalField(decimal_places=2, max_digits=11)), ('date', models.DateField()),
            ('description', models.TextField(blank=True)), ('created_at', models.DateTimeField(auto_now_add=True)),
        ], options={'ordering': ['-date', '-id']}),
    ]
