import pandas as pd
import os
from algorithms.genetic_scheduler import GeneticScheduler


class DataManager:
    def __init__(self):
        self.teachers_df = pd.DataFrame()
        self.classes_df = pd.DataFrame()
        self.classrooms_df = pd.DataFrame()
        self.courses_df = pd.DataFrame()
        self.tasks_df = pd.DataFrame()
        self.scheduler = None
        self.best_schedule = None
        self.scheduling_running = False
        self.current_generation = 0
        self.current_best_fitness = 0

    def load_from_excel(self, filepath):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")

        excel_file = pd.ExcelFile(filepath)
        sheet_names = excel_file.sheet_names

        required_sheets = ['教师信息表', '班级信息表', '教室信息表', '课程信息表', '教学任务表']
        for sheet in required_sheets:
            if sheet not in sheet_names:
                raise ValueError(f"Excel缺少必要的sheet: {sheet}")

        self.teachers_df = pd.read_excel(filepath, sheet_name='教师信息表')
        self.classes_df = pd.read_excel(filepath, sheet_name='班级信息表')
        self.classrooms_df = pd.read_excel(filepath, sheet_name='教室信息表')
        self.courses_df = pd.read_excel(filepath, sheet_name='课程信息表')
        self.tasks_df = pd.read_excel(filepath, sheet_name='教学任务表')

        self._validate_data()
        return True

    def _validate_data(self):
        required_teacher_fields = ['教师姓名', '工号', '所属院系', '住宿情况', '授课偏好', '联系电话', '不可授课时段']
        for field in required_teacher_fields:
            if field not in self.teachers_df.columns:
                raise ValueError(f"教师信息表缺少必要字段: {field}")

        required_class_fields = ['班级名称', '所属专业', '年级', '学生人数']
        for field in required_class_fields:
            if field not in self.classes_df.columns:
                raise ValueError(f"班级信息表缺少必要字段: {field}")

        required_classroom_fields = ['教室ID', '座位数', '教室类型']
        for field in required_classroom_fields:
            if field not in self.classrooms_df.columns:
                raise ValueError(f"教室信息表缺少必要字段: {field}")

        required_course_fields = ['课程ID', '课程名称', '学分', '周学时', '总学时', '连排要求', '教室类型要求', '是否允许晚间', '是否隔周上课']
        for field in required_course_fields:
            if field not in self.courses_df.columns:
                raise ValueError(f"课程信息表缺少必要字段: {field}")

        required_task_fields = ['任务ID', '课程', '授课教师', '授课班级', '周学时', '连排要求', '教室类型要求', '学期', '状态']
        for field in required_task_fields:
            if field not in self.tasks_df.columns:
                raise ValueError(f"教学任务表缺少必要字段: {field}")

    def run_scheduling(self):
        self.scheduling_running = True
        self.current_generation = 0
        self.current_best_fitness = 0

        self.scheduler = GeneticScheduler(
            self.teachers_df,
            self.classes_df,
            self.classrooms_df,
            self.courses_df,
            self.tasks_df
        )

        def progress_callback(generation, best_fitness, best_schedule):
            self.current_generation = generation
            self.current_best_fitness = best_fitness
            self.best_schedule = best_schedule

        result = self.scheduler.evolve(callback=progress_callback)
        self.best_schedule = result
        self.scheduling_running = False
        return result

    def get_timetable_data(self, view_type, filter_value, schedule=None):
        if schedule is None:
            schedule = self.best_schedule
        if schedule is None:
            return []
        if self.scheduler is None:
            return []

        schedule_list = self.scheduler.get_schedule_as_list(schedule)

        if view_type == 'teacher':
            return [item for item in schedule_list if item['teacher'] == filter_value]
        elif view_type == 'class':
            return [item for item in schedule_list if item['class_name'] == filter_value]
        elif view_type == 'classroom':
            return [item for item in schedule_list if item['classroom'] == filter_value]
        else:
            return schedule_list

    def export_to_excel(self, output_path):
        if self.best_schedule is None:
            raise ValueError("没有可导出的排课结果")

        if self.scheduler is None:
            raise ValueError("调度器未初始化")

        schedule_list = self.scheduler.get_schedule_as_list(self.best_schedule)
        df = pd.DataFrame(schedule_list)
        df.to_excel(output_path, index=False)
        return output_path

    def get_statistics(self):
        return {
            'teacher_count': len(self.teachers_df),
            'class_count': len(self.classes_df),
            'classroom_count': len(self.classrooms_df),
            'course_count': len(self.courses_df),
            'task_count': len(self.tasks_df)
        }

    def get_teachers(self):
        return self.teachers_df['教师姓名'].tolist() if not self.teachers_df.empty else []

    def get_classes(self):
        return self.classes_df['班级名称'].tolist() if not self.classes_df.empty else []

    def get_classrooms(self):
        return self.classrooms_df['教室ID'].tolist() if not self.classrooms_df.empty else []