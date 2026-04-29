import os
import json
import threading
import time
from flask import Flask, render_template, request, jsonify, send_file
from models.data_manager import DataManager

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'data'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

g_data_manager = DataManager()
g_best_schedule = None
g_scheduling_thread = None

def load_default_data():
    test_file = os.path.join(app.config['UPLOAD_FOLDER'], 'test_data.xlsx')
    if os.path.exists(test_file):
        try:
            g_data_manager.load_from_excel(test_file)
            print(f"预加载测试数据成功: 教师={len(g_data_manager.teachers_df)}, 班级={len(g_data_manager.classes_df)}, 教室={len(g_data_manager.classrooms_df)}, 课程={len(g_data_manager.courses_df)}, 任务={len(g_data_manager.tasks_df)}")
        except Exception as e:
            print(f"预加载测试数据失败: {e}")

load_default_data()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/scheduling')
def scheduling_page():
    return render_template('scheduling.html')


@app.route('/timetable')
def timetable_page():
    return render_template('timetable_simple.html')

@app.route('/test')
def test_page():
    return render_template('test.html')


@app.route('/api/upload', methods=['POST'])
def upload_file():
    global g_data_manager, g_best_schedule

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有上传文件'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'}), 400

    if file and file.filename.endswith('.xlsx'):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'uploaded_data.xlsx')
        file.save(filepath)

        try:
            g_data_manager.load_from_excel(filepath)
            g_best_schedule = None
            stats = g_data_manager.get_statistics()
            print(f"数据导入成功: 教师={stats['teacher_count']}, 班级={stats['class_count']}, 教室={stats['classroom_count']}, 课程={stats['course_count']}, 任务={stats['task_count']}")
            return jsonify({
                'success': True,
                'message': '数据导入成功',
                'statistics': stats
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500

    return jsonify({'success': False, 'message': '请上传xlsx格式的文件'}), 400


@app.route('/api/run-scheduling', methods=['POST'])
def run_scheduling():
    global g_data_manager, g_best_schedule, g_scheduling_thread

    if g_data_manager.tasks_df.empty:
        return jsonify({'success': False, 'message': '请先导入数据'}), 400

    task_count = len(g_data_manager.tasks_df)
    if task_count == 0:
        return jsonify({'success': False, 'message': '教学任务表为空'}), 400

    if g_scheduling_thread and g_scheduling_thread.is_alive():
        return jsonify({'success': False, 'message': '排课正在进行中'}), 400

    def scheduling_task():
        global g_best_schedule
        try:
            g_best_schedule = g_data_manager.run_scheduling()
            print(f"排课完成! 安排任务数: {len(g_best_schedule) if g_best_schedule else 0}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"排课出错: {e}")

    g_scheduling_thread = threading.Thread(target=scheduling_task)
    g_scheduling_thread.start()

    return jsonify({'success': True, 'message': '排课已开始', 'task_count': task_count})


@app.route('/api/scheduling-status')
def get_scheduling_status():
    global g_data_manager, g_best_schedule, g_scheduling_thread

    if g_scheduling_thread and g_scheduling_thread.is_alive():
        status = 'running'
    elif g_best_schedule is not None:
        status = 'completed'
    elif g_data_manager.best_schedule is not None:
        status = 'completed'
    else:
        status = 'idle'

    scheduled_count = 0
    if g_best_schedule:
        scheduled_count = len(g_best_schedule)
    elif g_data_manager.best_schedule:
        scheduled_count = len(g_data_manager.best_schedule)

    return jsonify({
        'status': status,
        'generation': g_data_manager.current_generation,
        'best_fitness': g_data_manager.current_best_fitness,
        'total_generations': 10,
        'scheduled_count': scheduled_count,
        'task_count': len(g_data_manager.tasks_df)
    })


@app.route('/api/timetable')
def get_timetable():
    global g_data_manager, g_best_schedule

    view_type = request.args.get('view_type', 'all')
    filter_value = request.args.get('filter_value', '')

    teachers = g_data_manager.get_teachers()
    classes = g_data_manager.get_classes()
    classrooms = g_data_manager.get_classrooms()

    current_schedule = g_best_schedule if g_best_schedule is not None else g_data_manager.best_schedule

    if current_schedule is None or g_data_manager.scheduler is None:
        return jsonify({
            'success': True,
            'data': [],
            'teachers': teachers,
            'classes': classes,
            'classrooms': classrooms,
            'days': ['周一', '周二', '周三', '周四', '周五'],
            'periods': ['1-2节', '3-4节', '5-6节', '7-8节', '9-11节']
        })

    timetable_data = g_data_manager.get_timetable_data(view_type, filter_value, current_schedule)

    return jsonify({
        'success': True,
        'data': timetable_data,
        'teachers': teachers,
        'classes': classes,
        'classrooms': classrooms,
        'days': ['周一', '周二', '周三', '周四', '周五'],
        'periods': ['1-2节', '3-4节', '5-6节', '7-8节', '9-11节']
    })


@app.route('/api/export')
def export_timetable():
    global g_data_manager

    if g_data_manager.best_schedule is None:
        return jsonify({'success': False, 'message': '没有可导出的排课结果'}), 400

    try:
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'timetable_result.xlsx')
        g_data_manager.export_to_excel(output_path)
        return send_file(output_path, as_attachment=True, download_name='timetable_result.xlsx')
    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500


@app.route('/api/statistics')
def get_statistics():
    global g_data_manager

    if g_data_manager.tasks_df.empty:
        return jsonify({
            'success': False,
            'message': '请先导入数据'
        }), 400

    stats = g_data_manager.get_statistics()
    return jsonify({
        'success': True,
        'statistics': stats
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)