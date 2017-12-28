jQuery(function($){
    $("#datatable").DataTable({
      "language": { "url": "//cdn.datatables.net/plug-ins/1.10.16/i18n/Japanese.json" },
      lengthMenu:[5, 10, 15, 20, 25, 50, 100],
      displayLength: 5,
      stateSave: true,
       order: [ [ 7, "desc" ] ],
   })
});
