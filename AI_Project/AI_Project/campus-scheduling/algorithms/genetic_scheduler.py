import numpy as np
import pandas as pd
import random
from copy import deepcopy


class GeneticScheduler:
    DAYS = ['周一', '周二', '周三', '周四', '周五']
    PERIODS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11']

    def __init__(self, teachers_df, classes_df, classrooms_df, courses_df, tasks_df):
        self.teachers_df = teachers_df
        self.classes_df = classes_df
        self.classrooms_df = classrooms_df
        self.courses_df = courses_df
        self.tasks_df = tasks_df
        self.best_schedule = None
        self.best_fitness = 0
        self._cache = {}
        self._build_cache()
        print(f"初始化: {len(self._all_tasks)} 任务, {len(self._cache['classroom_capacity'])} 教室")

    def _build_cache(self):
        self._cache['teacher_name'] = {}
        self._cache['teacher_unavailable'] = {}
        self._cache['teacher_at_home'] = {}
        
        for _, teacher in self.teachers_df.iterrows():
            name = str(teacher['教师姓名'])
            teacher_id = str(teacher['工号']) if '工号' in teacher else name
            self._cache['teacher_name'][teacher_id] = name
            self._cache['teacher_name'][name] = name
            
            unavailable = teacher['不可授课时段']
            slots = self._parse_unavailable_slots(unavailable)
            self._cache['teacher_unavailable'][name] = slots
            self._cache['teacher_at_home'][name] = str(teacher['住宿情况']) == '住家里'

        self._cache['course_name'] = {}
        self._cache['course_info'] = {}
        for _, course in self.courses_df.iterrows():
            course_id = str(course['课程ID'])
            course_name = str(course['课程名称'])
            self._cache['course_name'][course_id] = course_name
            self._cache['course_name'][course_name] = course_name
            self._cache['course_info'][course_name] = course.to_dict()

        self._cache['class_students'] = {}
        for _, cls in self.classes_df.iterrows():
            name = str(cls['班级名称'])
            self._cache['class_students'][name] = int(cls['学生人数'])

        self._cache['classroom_capacity'] = {}
        self._cache['classroom_type'] = {}
        for _, room in self.classrooms_df.iterrows():
            rid = str(room['教室ID'])
            self._cache['classroom_capacity'][rid] = int(room['座位数'])
            self._cache['classroom_type'][rid] = room.get('教室类型', '普通')

        self._all_tasks = []
        for _, task in self.tasks_df.iterrows():
            task_id = str(task['任务ID'])
            course_id_or_name = str(task['课程'])
            teacher_id_or_name = str(task['授课教师'])
            
            course_name = self._cache['course_name'].get(course_id_or_name, course_id_or_name)
            teacher_name = self._cache['teacher_name'].get(teacher_id_or_name, teacher_id_or_name)
            
            classes_str = str(task['授课班级'])
            class_list = [c.strip() for c in classes_str.split('、') if c.strip()]
            
            consecutive_req = str(task.get('连排要求', ''))
            room_type = str(task.get('教室类型要求', ''))
            
            for class_name in class_list:
                self._all_tasks.append({
                    'task_id': task_id,
                    'course': course_name,
                    'teacher': teacher_name,
                    'class_name': class_name,
                    'consecutive_req': consecutive_req,
                    'room_type': room_type
                })

        self._classrooms = list(self._cache['classroom_capacity'].keys())

    def _parse_unavailable_slots(self, unavailable_str):
        if pd.isna(unavailable_str) or not unavailable_str:
            return set()
        slots = set()
        try:
            for item in str(unavailable_str).split('、'):
                item = item.strip()
                if not item:
                    continue
                for day in self.DAYS:
                    if day in item:
                        for period in self.PERIODS:
                            if period in item:
                                slots.add((day, period))
                        break
        except:
            pass
        return slots

    def _get_slot_patterns(self, consecutive_req):
        patterns = []
        if '白天4节连排' in consecutive_req:
            patterns.append({'slots': ['1', '2', '3', '4'], 'start': '1', 'name': '1-4节'})
            patterns.append({'slots': ['5', '6', '7', '8'], 'start': '5', 'name': '5-8节'})
        if '晚间3节连排' in consecutive_req:
            patterns.append({'slots': ['9', '10', '11'], 'start': '9', 'name': '9-11节'})
        if '2节连排' in consecutive_req and '4节' not in consecutive_req:
            patterns.append({'slots': ['1', '2'], 'start': '1', 'name': '1-2节'})
            patterns.append({'slots': ['3', '4'], 'start': '3', 'name': '3-4节'})
            patterns.append({'slots': ['5', '6'], 'start': '5', 'name': '5-6节'})
            patterns.append({'slots': ['7', '8'], 'start': '7', 'name': '7-8节'})
        if not patterns:
            for i in range(1, 12):
                patterns.append({'slots': [str(i)], 'start': str(i), 'name': str(i)+'节'})
        return patterns

    def _generate_schedule(self):
        schedule = {}
        
        occupied_teachers = {day: {p: set() for p in self.PERIODS} for day in self.DAYS}
        occupied_classes = {day: {p: set() for p in self.PERIODS} for day in self.DAYS}
        occupied_rooms = {day: {p: set() for p in self.PERIODS} for day in self.DAYS}

        shuffled_tasks = self._all_tasks.copy()
        random.shuffle(shuffled_tasks)

        if not self._classrooms:
            print("错误: 没有教室!")
            return {}

        for task in shuffled_tasks:
            task_id = task['task_id']
            teacher = task['teacher']
            class_name = task['class_name']
            course = task['course']
            consecutive_req = task['consecutive_req']
            room_type = task['room_type']

            student_count = self._cache['class_students'].get(class_name, 0)
            
            suitable_rooms = []
            for rid, cap in self._cache['classroom_capacity'].items():
                rt = self._cache['classroom_type'].get(rid, '普通')
                if cap >= student_count:
                    if not room_type or room_type == '无要求' or rt == room_type:
                        suitable_rooms.append(rid)
            
            if not suitable_rooms:
                suitable_rooms = self._classrooms[:]

            patterns = self._get_slot_patterns(consecutive_req)
            random.shuffle(patterns)

            placed = False
            for pattern in patterns:
                if placed:
                    break
                
                needed_slots = pattern['slots']
                start_period = pattern['start']
                period_name = pattern['name']

                for day in self.DAYS:
                    if placed:
                        break

                    valid = True
                    for p in needed_slots:
                        if p not in self.PERIODS:
                            valid = False
                            break
                        if teacher in occupied_teachers[day][p]:
                            valid = False
                            break
                        if class_name in occupied_classes[day][p]:
                            valid = False
                            break
                        
                        if self._cache['teacher_at_home'].get(teacher, False) and p in ['9', '10', '11']:
                            valid = False
                            break
                        
                        unavailable = self._cache['teacher_unavailable'].get(teacher, set())
                        if (day, p) in unavailable:
                            valid = False
                            break

                    if not valid:
                        continue

                    for room_id in suitable_rooms:
                        room_ok = True
                        for p in needed_slots:
                            if room_id in occupied_rooms[day][p]:
                                room_ok = False
                                break

                        if room_ok:
                            schedule_key = f"{task_id}_{class_name}"
                            schedule[schedule_key] = {
                                'day': day,
                                'period': start_period,
                                'classroom': room_id,
                                'teacher': teacher,
                                'class_name': class_name,
                                'course': course,
                                'slots': needed_slots,
                                'period_name': period_name
                            }

                            for p in needed_slots:
                                occupied_teachers[day][p].add(teacher)
                                occupied_classes[day][p].add(class_name)
                                occupied_rooms[day][p].add(room_id)

                            placed = True
                            break

        print(f"生成: {len(schedule)} 任务")
        return schedule

    def _calculate_fitness(self, individual):
        if not individual:
            return 0
        return len(individual) / len(self._all_tasks) * 100

    def evolve(self, callback=None):
        best_schedule = {}
        best_fitness = 0

        for attempt in range(50):
            schedule = self._generate_schedule()
            fitness = self._calculate_fitness(schedule)
            
            if fitness > best_fitness:
                best_fitness = fitness
                best_schedule = schedule.copy()
                print(f"找到更好的方案: {len(best_schedule)}/{len(self._all_tasks)}")

            if best_fitness >= 95:
                break

        self.best_schedule = best_schedule
        self.best_fitness = best_fitness
        print(f"完成! 适应度={best_fitness:.1f}%, 任务={len(best_schedule)}")
        
        if callback:
            callback(0, best_fitness, best_schedule)

        return best_schedule

    def get_schedule_as_list(self, schedule):
        result = []
        for key, sched in schedule.items():
            for idx, period in enumerate(sched['slots']):
                result.append({
                    'task_id': sched.get('task_id', ''),
                    'course': sched['course'],
                    'teacher': sched['teacher'],
                    'class_name': sched['class_name'],
                    'day': sched['day'],
                    'period': period,
                    'classroom': sched['classroom'],
                    'classroom_name': sched['classroom'],
                    'credits': len(sched['slots']),
                    'slots_booked': len(sched['slots']),
                    'is_start': idx == 0,
                    'all_slots': sched['slots'],
                    'period_display': sched.get('period_name', ('第' + str(sched['slots'][0]) + '节') if len(sched['slots']) == 1 else ('第' + str(sched['slots'][0]) + '-' + str(sched['slots'][-1]) + '节'))
                })
        return result