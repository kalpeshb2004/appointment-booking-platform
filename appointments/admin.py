from django.contrib import admin

from .models import (Appointment, Department, Doctor, DoctorLeave,
                     DoctorSchedule, Hospital, Patient)


# Inline: parent page ke andar hi child rows edit
class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 1  # 1 khaali row add karne ke liye


class DoctorScheduleInline(admin.TabularInline):
    model = DoctorSchedule
    extra = 1


class DoctorLeaveInline(admin.TabularInline):
    model = DoctorLeave
    extra = 0


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "phone")
    search_fields = ("name", "city")
    inlines = [DepartmentInline]  # hospital page me hi departments


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "hospital")
    list_filter = ("hospital",)
    search_fields = ("name",)


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("user", "department", "consultation_fee", "slot_minutes", "is_active")
    list_filter = ("department__hospital", "department", "is_active")
    search_fields = ("user__username", "user__first_name")
    inlines = [DoctorScheduleInline, DoctorLeaveInline]  # schedule + leave isi page pe


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("user", "gender", "phone")
    search_fields = ("user__username", "phone")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "date", "start_time", "status")
    list_filter = ("status", "doctor__department", "date")
    search_fields = ("patient__user__username",)
    date_hierarchy = "date"
    actions = ["mark_completed", "mark_no_show"]

    # update() nahi, loop + save(): taaki model ka save() chale
    # aur active_slot sahi reset ho
    @admin.action(description="Mark as completed")
    def mark_completed(self, request, queryset):
        for appt in queryset:
            appt.status = "completed"
            appt.save()

    @admin.action(description="Mark as no-show")
    def mark_no_show(self, request, queryset):
        for appt in queryset:
            appt.status = "no_show"
            appt.save()
