(function () {
    angular
        .module('andyBeeApp')
        .controller('ManageFilterCtrl', ManageFilterCtrl);

    ManageFilterCtrl.$inject = ['$uibModalInstance', 'FilterService'];
    function ManageFilterCtrl($uibModalInstance, FilterService) {
        var vm = this;
        vm.serv = FilterService;
        vm.dismiss = dismiss_modal;
        vm.create_filter = create_filter;
        vm.delete_filter = delete_filter;
        vm.edit_filter = edit_filter;

        vm.filter_name = "";


        /// functions

        function dismiss_modal () {
            $uibModalInstance.dismiss(); 
        };

        function create_filter() {
            FilterService.create_filter(vm.filter_name, on_create_result);

            function on_create_result () {
                vm.filter_name = "";
            }
        }

        function delete_filter(idx) {
            FilterService.delete_filter(idx);
        }

        function edit_filter(idx) {
            FilterService.edit_filter(idx);
        }

    }
})();

