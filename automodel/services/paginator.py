from copy import deepcopy

from django.utils.safestring import mark_safe


class Pagination:
    """
    分页

    仅适用于python的django项目。

    如何使用：
        视图函数：
            pager = Pagination(request, len(data_list))
            new_data_list = data_list[pager.start:pager.end]

        模板：
            <div>
            {{ pager.html }}
            </div>
    """

    mode = ["full", "half", "base"]

    def __init__(self, request, data_length, page_key="page", per_page_num=10,
                 max_pager_count=11, mode=''):
        """
        :param request: 获取GET中的筛选条件和当前页码
        :param data_length: 操作的数据总长度
        :param page_key: GET中页码的键
        :param per_page_num: 每页显示的条数
        :param max_pager_count: 最大页码总数
        :param mode: 提供简洁版、数字版、完整版的分页显示
        """

        # 每页条数
        self.per_page_num = per_page_num

        # 总页数
        res, oth = divmod(data_length, self.per_page_num)
        self.total_pages = res if oth == 0 else res + 1
        self.pager_key = page_key

        # 当前页
        params = deepcopy(request.GET)
        params._mutable = True
        current_page = params.get(page_key, '')
        try:
            self.current_page = int(current_page)
        except ValueError as error:
            self.current_page = 1
        if self.current_page not in range(1, self.total_pages + 1):
            self.current_page = 1

        # 最大显示页码数(奇数)
        self.max_pager_count = max_pager_count
        self.half_max_pager_count = int((self.max_pager_count - 1) / 2)

        # url和原搜索条件
        self.base_url = request.path
        self.params = params

        # 页码模式
        self.mode = mode

        # 页码样式
        self.style = None

        # 页码组合
        self.pager_start = None
        self.pager_end = None
        self.li_list = None

        self.pager_previous = None
        self.pager_next = None
        self.pager_top = None
        self.pager_down = None

    @property
    def start(self):
        """起始位置"""
        return (self.current_page - 1) * self.per_page_num

    @property
    def end(self):
        """结束位置"""
        return self.current_page * self.per_page_num

    def html(self):
        """普通html代码"""
        self.style = False
        return mark_safe(''.join(self.pager_list))

    def bootstrap_html(self):
        """bootstrap样式的HTML"""
        self.style = True
        return mark_safe(''.join([
            '<nav aria-label="Page navigation"><ul class="pagination">', *self.pager_list, '</ul></nav>']))

    @property
    def pager_list(self):
        """"""
        if self.mode == "simple":
            self.pre_next_pager()
            pager_list = [self.pager_previous, self.pager_next]
        elif self.mode == "digital":
            self.digital_pager()
            pager_list = self.li_list
        else:
            self.digital_pager()
            self.pre_next_pager()
            self.top_down_pager()
            pager_list = [self.pager_top, self.pager_previous, *self.li_list, self.pager_next, self.pager_down]
        return pager_list

    def digital_pager(self):
        # 数字页码
        if self.total_pages < self.max_pager_count:
            self.pager_start = 1
            self.pager_end = self.total_pages
        else:
            if self.current_page <= self.half_max_pager_count:
                self.pager_start = 1
                self.pager_end = self.max_pager_count
            elif self.current_page >= (self.total_pages - self.half_max_pager_count):
                self.pager_start = self.total_pages - self.max_pager_count + 1
                self.pager_end = self.total_pages
            else:
                self.pager_start = self.current_page - self.half_max_pager_count
                self.pager_end = self.current_page + self.half_max_pager_count

        self.li_list = []
        # 生成a标签
        for j in range(self.pager_start, self.pager_end + 1):
            self.params[self.pager_key] = j
            if j == self.current_page:
                if self.style:
                    self.li_list.append("<li class='active'><a href='%s?%s'>%s</a></li>"
                                        % (self.base_url, self.params.urlencode(), j))
                else:
                    self.li_list.append("<a href='%s?%s' class='active'>%s</a>"
                                        % (self.base_url, self.params.urlencode(), j))
            else:
                if self.style:
                    self.li_list.append("<li><a href='%s?%s'>%s</a></li>" % (self.base_url, self.params.urlencode(), j))
                else:
                    self.li_list.append("<a href='%s?%s'>%s</a>" % (self.base_url, self.params.urlencode(), j))

    def top_down_pager(self):
        # 首页
        self.params[self.pager_key] = 1
        if self.current_page == 1:
            if self.style:
                self.pager_top = '<li class="disabled"><a href="%s?%s">首页</a></li>' \
                                 % (self.base_url, self.params.urlencode())
            else:
                self.pager_top = '<a>首页</a>'
        else:
            if self.style:
                self.pager_top = '<li><a href="%s?%s">首页</a><li>' % (self.base_url, self.params.urlencode())
            else:
                self.pager_top = '<a href="%s?%s">首页</a>' % (self.base_url, self.params.urlencode())

        # 尾页
        self.params[self.pager_key] = self.total_pages
        if self.current_page == self.total_pages:
            if self.style:
                self.pager_down = '<li class="disabled"><a href="%s?%s">尾页</a></li>' \
                                  % (self.base_url, self.params.urlencode())
            else:
                self.pager_down = '<a>尾页</a>'
        else:
            if self.style:
                self.pager_down = '<li><a href="%s?%s">尾页</a></li>' \
                                  % (self.base_url, self.params.urlencode())
            else:
                self.pager_down = '<a href="%s?%s">尾页</a>' % (self.base_url, self.params.urlencode())

    def pre_next_pager(self):
        # 上一页
        if self.current_page == 1:
            self.params[self.pager_key] = self.current_page
            if self.style:
                self.pager_previous = '<li class="previous disabled"><a href="%s?%s">上一页</a></li>' \
                                      % (self.base_url, self.params.urlencode())
            else:
                self.pager_previous = '<a>上一页</a>'
        else:
            self.params[self.pager_key] = self.current_page - 1
            if self.style:
                self.pager_previous = '<li class="previous"><a href="%s?%s">上一页</a></li>' \
                                      % (self.base_url, self.params.urlencode())
            else:
                self.pager_previous = '<a href="%s?%s">上一页</a>' \
                                      % (self.base_url, self.params.urlencode())

        # 下一页
        if self.current_page == self.total_pages:
            self.params[self.pager_key] = self.current_page
            if self.style:
                self.pager_next = '<li class="next disabled"><a href="%s?%s">下一页</a></li>' \
                                  % (self.base_url, self.params.urlencode())
            else:
                self.pager_next = '<a>下一页</a>'
        else:
            self.params[self.pager_key] = self.current_page + 1
            if self.style:
                self.pager_next = '<li class="next"><a href="%s?%s">下一页</a></li>' \
                                  % (self.base_url, self.params.urlencode())
            else:
                self.pager_next = '<a href="%s?%s">下一页</a>' \
                                  % (self.base_url, self.params.urlencode())
