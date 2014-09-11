/*
Copyright (c) 2003-2011, CKSource - Frederico Knabben. All rights reserved.
For licensing, see LICENSE.html or http://ckeditor.com/license
*/
CKEDITOR.editorConfig = function(config) {
  config.toolbar = 'Appy';
  config.toolbar_Appy = [
    { name: 'basicstyles',
      items: ["Format", "Bold", "Italic", "Underline"]},
    { name: 'paragraph',
      items: ["NumberedList", "BulletedList", "Outdent", "Indent"]},
    { name: 'clipboard',
      items: ["Cut", "Copy", "Paste", "PasteText", "Undo", "Redo"]},
    { name: 'editing', items: ["Scayt"]},
    { name: 'insert',
      items: ["Image", "Table", "SpecialChar", "Link", "Unlink", "Source", "Maximize"]}
  ];
  config.entities = false;
  config.entities_greek = false;
  config.entities_latin = false;
  config.fillEmptyBlocks = false;
  config.removePlugins = 'elementspath';
  config.scayt_sLang = 'fr_BE';
  config.scayt_uiTabs = '0,1,0';
  config.removeDialogTabs = 'image:advanced;link:advanced';
};

