"""
@File    :   data_filter.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""
from sqlalchemy import or_, func


def judge(file_dict, name, value):
    if name not in file_dict:
        file_dict[name] = value
    else:
        tmp_dict: dict = file_dict[name]
        if name == "$and":
            file_dict[name] = file_dict.pop(name) + [{name: value}]
        elif name == "$or":
            tmp_d = [{"$and": [{name: file_dict.pop(name)}, {name: value}]}]
            if file_dict.get("$and"):
                file_dict['$and'] = file_dict.pop("$and") + tmp_d
            else:
                file_dict['$and'] = tmp_d
        else:
            if list(value.keys())[0] in list(tmp_dict.keys()):
                tmp_d = [{name: file_dict.pop(name)}, {name: value}]
                judge(file_dict, '$and', tmp_d)
            else:
                tmp_dict.update(value)
                file_dict[name] = tmp_dict
    return file_dict


def get_filter(filter_list: list = []):
    filters_dict = {}
    if filter_list:
        for i in filter_list:
            name = i['name']
            try:
                if i['type'] == "int":
                    i['value'] = float(i['value'])
            except Exception:
                pass
            if i['exp'] == 'equal':
                judge(filters_dict, name, {"$eq": i['value']})
            elif i['exp'] == 'gt':
                judge(filters_dict, name, {"$gt": i['value']})
            elif i['exp'] == 'lt':
                judge(filters_dict, name, {"$lt": i['value']})
            elif i['exp'] == 'gte':
                judge(filters_dict, name, {"$gte": i['value']})
            elif i['exp'] == 'lte':
                judge(filters_dict, name, {"$lte": i['value']})
            elif i['exp'] == 'abs':
                lp = [{i['name']: {"$gte": i["value"]}}, {i['name']: {"$lte": i["value"] * -1}}]
                judge(filters_dict, "$or", lp)
                # filters_dict['$or'] = l
            elif i['exp'] == 'notnull':
                judge(filters_dict, name, {"$ne": "null"})
                judge(filters_dict, name, {"$ne": ""})
            elif i['exp'] == 'like':
                judge(filters_dict, name, {"$regex": i['value'], '$options': 'i'})
            elif i['exp'] == 'notContain':
                judge(filters_dict, name, {"$nin": i['value']})
            elif i['exp'] == 'contain':
                try:
                    judge(filters_dict, name, {"$in": [j.strip() for j in i['value']]})
                except Exception:
                    judge(filters_dict, name, {"$in": i['value']})
            elif i['exp'] == "exists":
                judge(filters_dict, name, {"$exists": i['value']})
            elif i['exp'] == 'range':
                try:
                    filters_dict[i['name']] = {"$gt": float(i['value'].split(',')[0]), "$lte": float(i['value'].split(',')[1])}
                except Exception as e:
                    print(e)
    return filters_dict


def apply_filters(query, model, filters=[], search=None, filter_exp_or=[]):
    """
    :param query: sql
    :param model: db model
    :param search
    :param filter_exp_or
    :param filters: [{"name":'xx',"exp":"xx","value":"xx"}] <=list
    :return:
    """
    if search:
        if len(search) == 1:
            query = query.filter(or_(getattr(model, search[0]['name']).in_(search[0]['value'])))
        else:
            query = query.filter(or_(getattr(model, search[0]['name']).in_(search[0]['value']), func.lower(getattr(model, search[1]['name'])).in_(search[1]['value'])))
    for i in filters:
        if i['exp'] == "equal":
            query = query.filter(getattr(model, i['name']) == ("%s" % i['value']))
        elif i['exp'] == "gt":
            query = query.filter(getattr(model, i['name']) > ("%s" % i['value']))
        elif i['exp'] == "lt":
            query = query.filter(getattr(model, i['name']) < ("%s" % i['value']))
        elif i['exp'] == "gte":
            query = query.filter(getattr(model, i['name']) >= ("%s" % i['value']))
        elif i['exp'] == "lte":
            query = query.filter(getattr(model, i['name']) <= ("%s" % i['value']))
        elif i['exp'] == "like":
            query = query.filter(getattr(model, i['name']).ilike("%%%s%%" % i['value']))
        elif i['exp'] == "notContain":
            if isinstance(i['value'], list):
                query = query.filter(getattr(model, i['name']).notin_(i['value']))
            else:
                query = query.filter(getattr(model, i['name']).notin_(i['value'].split(',')))
        elif i['exp'] == "contain":
            if isinstance(i['value'], list):
                query = query.filter(getattr(model, i['name']).in_(i['value']))
            else:
                query = query.filter(getattr(model, i['name']).in_(i['value'].split(',')))
        elif i['exp'] == "range":
            query = query.filter(getattr(model, i['name']).like("%%%s%%" % i['value']))
        elif i['exp'] == "notnull":
            query = query.filter(getattr(model, i['name']).isnot(None))
        elif i['exp'] == "startswith":
            query = query.filter(getattr(model, i['name']).startswith(i['value']))
        elif i['exp'] == "abs":
            query = query.filter(or_(getattr(model, i['name']) >= ("%s" % i['value']), getattr(model, i['name']) < ("%s" % -i['value'])))
        elif i['exp'] == "or_equal":
            query = query.filter(or_(getattr(model, i['name'][0]) == ("%s" % i['value'][0]), getattr(model, i['name'][1]) == ("%s" % i['value'][1])))
        else:
            query = query
    for n in filter_exp_or:
        if n['exp'] == "notnull":
            filters = []
            for ii in n['value']:
                filters.append(getattr(model, ii).isnot(None))
            query = query.filter(or_(*filters))
        if n['exp'] == "like":
            filters = []
            value = n['value']
            for nn in n['name']:
                filters.append(getattr(model, nn).like("%%%s%%" % value))
            query = query.filter(or_(*filters))
    return query


__all__ = ['apply_filters', 'get_filter', 'judge']
