/*
Copyright (c) 2003-2011, CKSource - Frederico Knabben. All rights reserved.
For licensing, see LICENSE.html or http://ckeditor.com/license
*/

CKEDITOR.editorConfig = function( config )
{
  config.toolbar = 'Appy';
  config.toolbar_Appy =
  [
    { name: 'basicstyles', items : [ 'Format', 'Bold', 'Italic', 'Underline',
                                     'Strike', 'Subscript', 'Superscript'] },
    { name: 'paragraph', items : [ 'NumberedList', 'BulletedList', '-',
                                   'Outdent', 'Indent', '-', 'JustifyLeft',
                                   'JustifyCenter', 'JustifyRight',
                                   'JustifyBlock'] },
    { name: 'clipboard', items : [ 'Cut', 'Copy', 'Paste', 'PasteText',
                                   'PasteFromWord', 'Undo', 'Redo']},
    { name: 'editing', items : [ 'Find', 'Replace', '-', 'SelectAll', '-',
                                 'SpellChecker', 'Scayt']},
    { name: 'insert', items : [ 'Image', 'Table', 'SpecialChar', 'Link',
                                'Unlink', 'Source', 'Maximize']},
  ];
  config.toolbar_AppyRich = config.toolbar_Appy.concat(
    [{name: 'styles', items: [ 'Font', 'FontSize', 'TextColor', 'BGColor',
                               'RemoveFormat' ]},]
  )
  config.format_p =  { element:'p',  attributes:{'style':'margin:0;padding:0'}};
  config.format_h1 = { element:'h1', attributes:{'style':'margin:0;padding:0'}};
  config.format_h2 = { element:'h2', attributes:{'style':'margin:0;padding:0'}};
  config.format_h3 = { element:'h3', attributes:{'style':'margin:0;padding:0'}};
  config.format_h4 = { element:'h4', attributes:{'style':'margin:0;padding:0'}};
};
