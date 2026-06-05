from django.db import models
from django_tenants.utils import schema_context
from django_tenants_auth.core.models import TimeStampedModel


class Department(TimeStampedModel):
    """Department model (tenant-scoped)."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children'
    )
    manager = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments'
    )

    class Meta:
        unique_together = ['slug']

    def __str__(self):
        return self.name


class Employee(TimeStampedModel):
    """Employee model (tenant-scoped)."""
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('on_leave', 'On Leave'),
        ('terminated', 'Terminated'),
    ]
    
    # Basic Info
    name = models.CharField(max_length=200)
    emp_id = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    
    # Department & Designation
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        related_name='employees'
    )
    designation = models.CharField(max_length=100)
    
    # Compensation
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    commission = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Contact Info
    mobile_number = models.CharField(max_length=20, blank=True)
    
    # Personal Info
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='male')
    blood_group = models.CharField(max_length=5, blank=True)
    religion = models.CharField(max_length=50, blank=True)
    
    # Employment Dates
    appointment_date = models.DateField(null=True, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    
    # Additional Info
    address = models.TextField(blank=True)
    image_path = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # User association (optional)
    user = models.OneToOneField(
        'tenants.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employee_profile'
    )
    
    # Metadata
    created_by = models.ForeignKey(
        'tenants.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_employees'
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.emp_id})"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(f"{self.name}-{self.emp_id}")
        super().save(*args, **kwargs)